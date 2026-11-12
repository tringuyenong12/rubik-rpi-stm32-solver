from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import queue
import threading
import time
from typing import Any

from rubik_robot.cube.scramble import (
    apply_move,
    apply_moves,
    create_scramble_problem,
    explain_move,
    generate_scramble,
)
from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE, validate_cube_string
from rubik_robot.motion.planner import MotionPlanner, PlannedAction
from rubik_robot.protocol import Command
from rubik_robot.solver.kociemba_solver import solve_cube


# Mapping faces to actuators as defined in docs/ACTUATOR_MAPPING.md
_FACE_TO_ACTUATOR = {
    "R": {"carriage": "carriage_ne", "tool": "tool_ne"},
    "L": {"carriage": "carriage_sw", "tool": "tool_sw"},
    "F": {"carriage": "carriage_se", "tool": "tool_se"},
    "B": {"carriage": "carriage_nw", "tool": "tool_nw"},
    "U": {"carriage": "center_lift", "tool": "center_rotate"},
    "D": {"carriage": "center_lift", "tool": "center_rotate"},
}

_INITIAL_ACTUATORS = {
    "carriage_nw": "HOME",
    "carriage_ne": "HOME",
    "carriage_sw": "HOME",
    "carriage_se": "HOME",
    "tool_nw": "HOME",
    "tool_ne": "HOME",
    "tool_sw": "HOME",
    "tool_se": "HOME",
    "center_lift": "HOME",
    "center_rotate": "HOME",
}


class RobotWebController:
    """Central controller managing real-time cube state, mechanical solver execution,
    and live web client streaming."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.current_cube: str = SOLVED_CUBE
        self.solver_state: str = "IDLE"  # IDLE, SOLVING, PAUSED, STOPPED, DONE, ERROR
        self.hardware_mode: str = "simulated"  # "simulated" or "serial"
        self.serial_port: str = "/dev/ttyAMA0"
        self.baudrate: int = 115200
        self.face_turn_command: str = "TURN"  # "TURN" or "MOVE"
        self.default_duration_ms: int = 450

        # Solution tracking
        self.solution_tokens: list[str] = []
        self.planned_actions: list[PlannedAction] = []
        self.current_step_index: int = 0
        self.total_steps: int = 0
        self.active_action_info: dict[str, Any] | None = None
        self.solve_start_time: float | None = None
        self.elapsed_ms: int = 0
        self.error_message: str = ""

        # Actuators
        self.actuator_states: dict[str, str] = dict(_INITIAL_ACTUATORS)

        # Wire logging (keeps last 200 logs)
        self.logs: deque[dict[str, str]] = deque(maxlen=200)

        # SSE client queues
        self.subscribers: set[queue.Queue] = set()

        # Threading controls for execution
        self._worker_thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._pause_requested = threading.Event()
        self._step_once = threading.Event()

    def log(self, direction: str, message: str) -> None:
        """Record a UART wire frame or status message and broadcast to clients."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = {
            "timestamp": timestamp,
            "direction": direction,  # "->", "<-", or "INFO"
            "message": message,
        }
        with self.lock:
            self.logs.append(entry)
        self.broadcast("log", entry)

    def subscribe(self) -> queue.Queue:
        """Register a new SSE subscriber queue."""
        q = queue.Queue(maxsize=100)
        with self.lock:
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Unregister an SSE subscriber queue."""
        with self.lock:
            self.subscribers.discard(q)

    def broadcast(self, event_type: str, data: Any) -> None:
        """Send an SSE event to all connected web clients."""
        payload = {"event": event_type, "data": data}
        with self.lock:
            dead_queues = []
            for q in list(self.subscribers):
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead_queues.append(q)
            for q in dead_queues:
                self.subscribers.discard(q)

    def get_status(self) -> dict[str, Any]:
        """Return the complete snapshot of the robot and solver state."""
        with self.lock:
            return {
                "cube": self.current_cube,
                "is_solved": self.current_cube == SOLVED_CUBE,
                "solver_state": self.solver_state,
                "hardware_mode": self.hardware_mode,
                "serial_port": self.serial_port,
                "baudrate": self.baudrate,
                "face_turn_command": self.face_turn_command,
                "default_duration_ms": self.default_duration_ms,
                "solution": self.solution_tokens,
                "current_step": self.current_step_index,
                "total_steps": self.total_steps,
                "active_action": self.active_action_info,
                "elapsed_ms": self.elapsed_ms,
                "actuators": dict(self.actuator_states),
                "error_message": self.error_message,
                "recent_logs": list(self.logs)[-30:],
            }

    def set_cube(self, cube_str: str) -> dict[str, Any]:
        """Set cube string directly (e.g. from camera scan or web editor)."""
        validate_cube_string(cube_str)
        with self.lock:
            if self.solver_state == "SOLVING":
                raise RuntimeError("Cannot change cube while solving is in progress")
            self.current_cube = cube_str
            self.solver_state = "IDLE" if cube_str != SOLVED_CUBE else "DONE"
            self.solution_tokens = []
            self.planned_actions = []
            self.current_step_index = 0
            self.total_steps = 0
            self.active_action_info = None
            self.error_message = ""
        self.log("INFO", f"Cube state updated: {cube_str[:12]}...")
        self.broadcast("status", self.get_status())
        return self.get_status()

    def reset_cube(self) -> dict[str, Any]:
        """Reset the cube to the solved state."""
        return self.set_cube(SOLVED_CUBE)

    def scramble_cube(self, level: str = "medium") -> dict[str, Any]:
        """Generate a scramble according to difficulty and apply to current state."""
        with self.lock:
            if self.solver_state == "SOLVING":
                raise RuntimeError("Cannot scramble while solving is in progress")

        problem = create_scramble_problem(level=level)
        with self.lock:
            self.current_cube = problem["cube"]
            self.solver_state = "IDLE"
            self.solution_tokens = problem["solution_moves"]
            self.planned_actions = []
            self.current_step_index = 0
            self.total_steps = len(self.solution_tokens)
            self.active_action_info = None
            self.error_message = ""

        self.log("INFO", f"Scramble applied ({level}): {problem['scramble']}")
        self.broadcast("status", self.get_status())
        return {
            **self.get_status(),
            "scramble": problem["scramble"],
            "scramble_moves": problem["scramble_moves"],
        }

    def apply_single_move(self, move_token: str) -> dict[str, Any]:
        """Manually rotate one face (e.g. from manual move button)."""
        with self.lock:
            if self.solver_state == "SOLVING":
                raise RuntimeError("Cannot execute manual move while automatic solving is active")

        new_cube = apply_move(self.current_cube, move_token)
        planner = MotionPlanner(
            default_duration_ms=self.default_duration_ms,
            face_turn_command=self.face_turn_command,
        )
        actions = planner.plan(move_token)
        wire_cmd = actions[0].to_wire() if actions else move_token

        self.log("->", wire_cmd)
        self.log("<-", f"OK {self.face_turn_command}")
        self.log("<-", f"DONE {self.face_turn_command}")

        with self.lock:
            self.current_cube = new_cube
            if self.current_cube == SOLVED_CUBE:
                self.solver_state = "DONE"
            else:
                self.solver_state = "IDLE"
            # recalculate solution preview if not solved
            if self.current_cube != SOLVED_CUBE:
                sol = solve_cube(self.current_cube)
                self.solution_tokens = sol.split() if sol else []
                self.total_steps = len(self.solution_tokens)
                self.current_step_index = 0
            else:
                self.solution_tokens = []
                self.total_steps = 0
                self.current_step_index = 0

        self.broadcast("status", self.get_status())
        return self.get_status()

    def start_solve(
        self,
        cube_str: str | None = None,
        duration_ms: int | None = None,
        face_turn_command: str | None = None,
        hardware_mode: str | None = None,
        port: str | None = None,
    ) -> dict[str, Any]:
        """Initiate solving sequence with real-time mechanical or simulated execution."""
        with self.lock:
            if self.solver_state == "SOLVING":
                return self.get_status()

            if cube_str:
                validate_cube_string(cube_str)
                self.current_cube = cube_str

            if duration_ms is not None:
                self.default_duration_ms = duration_ms
            if face_turn_command in {"TURN", "MOVE"}:
                self.face_turn_command = face_turn_command
            if hardware_mode in {"simulated", "serial"}:
                self.hardware_mode = hardware_mode
            if port:
                self.serial_port = port

            if self.current_cube == SOLVED_CUBE:
                self.solver_state = "DONE"
                return self.get_status()

            # Generate solution
            solution_str = solve_cube(self.current_cube)
            if not solution_str:
                self.solver_state = "DONE"
                return self.get_status()

            planner = MotionPlanner(
                default_duration_ms=self.default_duration_ms,
                face_turn_command=self.face_turn_command,
            )
            self.planned_actions = planner.plan(solution_str)
            self.solution_tokens = solution_str.split()
            self.total_steps = len(self.planned_actions)
            self.current_step_index = 0
            self.solver_state = "SOLVING"
            self.error_message = ""
            self.solve_start_time = time.time()
            self.elapsed_ms = 0

            self._stop_requested.clear()
            self._pause_requested.clear()
            self._step_once.clear()

        self.log("INFO", f"Starting mechanical solver [{self.hardware_mode}]")
        self.log("INFO", f"Solution: {solution_str} ({len(self.planned_actions)} moves)")
        self.broadcast("status", self.get_status())

        # Start background worker thread
        self._worker_thread = threading.Thread(target=self._run_solving_worker, daemon=True)
        self._worker_thread.start()
        return self.get_status()

    def pause(self) -> dict[str, Any]:
        """Pause real-time solving."""
        with self.lock:
            if self.solver_state == "SOLVING":
                self.solver_state = "PAUSED"
                self._pause_requested.set()
                self.log("INFO", "Solving paused by user")
        self.broadcast("status", self.get_status())
        return self.get_status()

    def resume(self) -> dict[str, Any]:
        """Resume solving from paused state."""
        with self.lock:
            if self.solver_state == "PAUSED":
                self.solver_state = "SOLVING"
                self._pause_requested.clear()
                self._step_once.set()  # unblock if waiting in step
                self.log("INFO", "Solving resumed")
        self.broadcast("status", self.get_status())
        return self.get_status()

    def step(self) -> dict[str, Any]:
        """Step one single move forward when paused."""
        with self.lock:
            if self.solver_state == "PAUSED":
                self._step_once.set()
                self.log("INFO", "Step forward requested")
        return self.get_status()

    def stop(self) -> dict[str, Any]:
        """Abort solving immediately and send STOP wire command."""
        with self.lock:
            self._stop_requested.set()
            self._pause_requested.clear()
            self._step_once.set()
            self.solver_state = "STOPPED"
            self.active_action_info = None

        self.log("->", "STOP")
        self.log("<-", "OK STOP")
        self.log("INFO", "Solving aborted by user")
        self._reset_actuators()
        self.broadcast("status", self.get_status())
        return self.get_status()

    def _reset_actuators(self) -> None:
        with self.lock:
            self.actuator_states = dict(_INITIAL_ACTUATORS)
        self.broadcast("actuators", self.actuator_states)

    def _run_solving_worker(self) -> None:
        """Background thread executing the motion plan in real-time."""
        serial_conn = None
        try:
            if self.hardware_mode == "serial":
                try:
                    from rubik_robot.transport.serial_link import SerialLink

                    serial_conn = SerialLink(
                        port=self.serial_port,
                        baudrate=self.baudrate,
                        timeout_s=3.0,
                    )
                    serial_conn.open()
                    self.log("INFO", f"Serial connection opened on {self.serial_port}")

                    # Handshake PING & HOME
                    self.log("->", "PING")
                    pong = serial_conn.request(Command("PING"))
                    self.log("<-", pong)

                    self.log("->", "HOME")
                    home_ack = serial_conn.request(Command("HOME"))
                    self.log("<-", home_ack)
                except Exception as ex:
                    self.log("ERR", f"Serial connection failed: {ex}. Falling back to simulation.")
                    self.hardware_mode = "simulated"
                    serial_conn = None
            else:
                # Simulated hardware handshake
                self.log("->", "PING")
                time.sleep(0.05)
                self.log("<-", "OK PONG")

                self.log("->", "HOME")
                time.sleep(0.05)
                self.log("<-", "OK HOME")
                time.sleep(0.15)
                self.log("<-", "DONE HOME")

            # Execute planned actions one by one
            for i, action in enumerate(self.planned_actions):
                if self._stop_requested.is_set():
                    break

                # Handle pause
                while self._pause_requested.is_set():
                    if self._stop_requested.is_set():
                        break
                    # Wait for step or resume
                    if self._step_once.wait(timeout=0.2):
                        self._step_once.clear()
                        break

                if self._stop_requested.is_set():
                    break

                move_token = self.solution_tokens[i] if i < len(self.solution_tokens) else action.command.face
                face = action.command.face
                turns = action.command.turns
                duration_ms = action.command.duration_ms
                wire_cmd = action.to_wire()

                # Actuator assignment
                act_info = _FACE_TO_ACTUATOR.get(face, {"carriage": "carriage_ne", "tool": "tool_ne"})
                carriage_role = act_info["carriage"]
                tool_role = act_info["tool"]

                action_detail = {
                    "step": i + 1,
                    "total": self.total_steps,
                    "token": move_token,
                    "face": face,
                    "turns": turns,
                    "duration_ms": duration_ms,
                    "wire": wire_cmd,
                    "carriage": carriage_role,
                    "tool": tool_role,
                    "desc_vi": explain_move(move_token, "vi"),
                    "desc_en": explain_move(move_token, "en"),
                }

                with self.lock:
                    self.current_step_index = i + 1
                    self.active_action_info = action_detail
                    self.actuator_states[carriage_role] = "ENGAGED"
                    self.actuator_states[tool_role] = "TURNING"

                self.log("->", wire_cmd)
                self.broadcast("move_start", action_detail)
                self.broadcast("actuators", self.actuator_states)

                # Hardware vs Simulated execution
                if serial_conn is not None:
                    try:
                        reply = serial_conn.request(action.command)
                        self.log("<-", reply)
                    except Exception as ex:
                        self.log("ERR", f"UART communication error: {ex}")
                else:
                    # Simulated execution matching real timing
                    time.sleep(0.03)
                    self.log("<-", f"OK {self.face_turn_command}")

                    # Sleep in increments of 30ms to allow responsive stop/pause
                    elapsed = 0.0
                    target_s = duration_ms / 1000.0
                    while elapsed < target_s:
                        if self._stop_requested.is_set():
                            break
                        step_s = min(0.03, target_s - elapsed)
                        time.sleep(step_s)
                        elapsed += step_s

                    self.log("<-", f"DONE {self.face_turn_command}")

                # Update cube state
                new_cube = apply_move(self.current_cube, move_token)
                with self.lock:
                    self.current_cube = new_cube
                    self.actuator_states[carriage_role] = "HOME"
                    self.actuator_states[tool_role] = "HOME"
                    if self.solve_start_time:
                        self.elapsed_ms = int((time.time() - self.solve_start_time) * 1000)

                self.broadcast("move_done", {
                    "step": i + 1,
                    "total": self.total_steps,
                    "token": move_token,
                    "cube": new_cube,
                    "is_solved": new_cube == SOLVED_CUBE,
                })
                self.broadcast("actuators", self.actuator_states)

                # Small delay between consecutive moves for mechanical safety
                time.sleep(0.08)

            # Finishing
            with self.lock:
                if not self._stop_requested.is_set():
                    self.solver_state = "DONE"
                    self.active_action_info = None

            if not self._stop_requested.is_set():
                self.log("INFO", "Solve finished successfully! Cube is solved.")
            self._reset_actuators()
            self.broadcast("solve_completed", self.get_status())

        except Exception as e:
            with self.lock:
                self.solver_state = "ERROR"
                self.error_message = str(e)
                self.active_action_info = None
            self._reset_actuators()
            self.log("ERR", f"Solving error: {e}")
            self.broadcast("status", self.get_status())
        finally:
            if serial_conn is not None:
                try:
                    serial_conn.close()
                except Exception:
                    pass


# Global singleton instance
robot_controller = RobotWebController()
