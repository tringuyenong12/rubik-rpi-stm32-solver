"""Validate a solver plan against its initial cube before opening UART."""
from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.solver.kociemba_solver import solve_cube
from rubik_robot.transport.scramble_sender import send_actions
from twophase.face import FaceCube
from twophase.cubie import basicMoveCube, CUBE_OK


def solution_plan(cube, solution=None, duration_ms=450):
    validate_cube_string(cube)
    face = FaceCube()
    if face.from_string(cube) is not True:
        raise ValueError('Invalid cube definition')
    cubie = face.to_cubie_cube()
    if cubie.verify() != CUBE_OK:
        raise ValueError('Cube is not physically solvable')
    solution = solve_cube(cube) if solution is None else solution
    actions = MotionPlanner(default_duration_ms=duration_ms).plan(solution)
    for action in actions:
        move = action.command
        for _ in range(move.turns % 4):
            cubie.multiply(basicMoveCube['URFDLB'.index(move.face)])
    if cubie.to_facelet_cube().to_string() != SOLVED_CUBE:
        raise ValueError('Solution does not solve the supplied cube; no UART commands sent')
    return solution, actions


def send_solution(cube, port, baudrate=115200, solution=None,
                  cancel=None, progress=None, timeout_s=30):
    _, actions = solution_plan(cube, solution)
    return send_actions(actions, port, baudrate, cancel, progress, timeout_s)
