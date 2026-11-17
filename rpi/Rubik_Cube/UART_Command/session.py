"""STM32 transaction: #ID command -> >#ID OK -> >#ID DONE (or ERR)."""
import math
import re
import threading
import time

import serial


class UARTSession:
    """One outstanding command. A failed session never retries motion."""

    _ports = set()
    _ports_lock = threading.Lock()

    def __init__(self, port='/dev/serial0', baudrate=115200,
                 done_timeout=30.0, ok_timeout=1.0):
        if not port or baudrate <= 0:
            raise ValueError('Specify a UART port and positive baudrate')
        for timeout in (done_timeout, ok_timeout):
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError('UART timeouts must be finite and positive')
        self.port, self.baudrate = port, baudrate
        self.done_timeout, self.ok_timeout = done_timeout, ok_timeout
        self.serial = None
        self.command_id = 0
        self.failed = False
        self.last_error = None
        self.lock = threading.RLock()

    def open(self):
        with self.lock:
            if self.serial is None:
                with self._ports_lock:
                    if self.port in self._ports:
                        raise RuntimeError(f'UART port already in use by this application: {self.port}')
                    self.serial = serial.Serial(port=self.port, baudrate=self.baudrate,
                                                timeout=.1, write_timeout=1.0)
                    self._ports.add(self.port)
            return self.serial

    def close(self):
        with self.lock:
            if self.serial is not None:
                try:
                    self.serial.close()
                finally:
                    self.serial = None
                    with self._ports_lock:
                        self._ports.discard(self.port)

    def request(self, command, timeout_s=None):
        """Return matching DONE; mark failed transactions unusable until replaced."""
        timeout = self.done_timeout if timeout_s is None else timeout_s
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('UART timeout must be finite and positive')
        if not isinstance(command, str) or not re.fullmatch(
                r'[A-Z0-9_]+(?: [A-Za-z0-9_.+\-]+)*', command):
            raise ValueError('Expected one ASCII command body without #ID or newline')
        with self.lock:
            if self.failed:
                raise RuntimeError('UART session failed; check cube state and reconnect')
            if self.command_id >= 65535:
                raise RuntimeError('UART IDs exhausted; start a new session')
            next_id = self.command_id + 1
            frame = f'#{next_id} {command}\n'.encode('ascii')
            if len(frame) - 2 > 63:
                raise ValueError('Command exceeds STM32 receive buffer')
            self.last_error = None
            try:
                uart = self.open()
                self.command_id = next_id
                if uart.write(frame) != len(frame):
                    raise OSError('Incomplete UART write; movement unconfirmed')
                uart.flush()
                print(f'[TX] {frame.decode().strip()}')
                deadline = time.monotonic() + min(self.ok_timeout, timeout)
                acknowledged = False
                pending = bytearray()
                while time.monotonic() < deadline:
                    uart.timeout = min(.1, max(.001, deadline - time.monotonic()))
                    pending.extend(uart.readline())
                    if len(pending) > 4096:
                        raise RuntimeError('UART response exceeds 4096 bytes')
                    while b'\n' in pending:
                        line, _, rest = pending.partition(b'\n')
                        pending = bytearray(rest)
                        text = line.decode('ascii', errors='replace').strip()
                        print(f'[RX] {text}')
                        match = re.fullmatch(r'>#(\d+) (OK|DONE|ERR)(?: (.*))?', text)
                        if match is None or int(match[1]) != next_id:
                            continue
                        status, detail = match[2], match[3]
                        if status == 'ERR':
                            raise RuntimeError(f'STM32 #{next_id}: {detail or "ERR"}')
                        if status == 'OK' and detail is None and not acknowledged:
                            acknowledged = True
                            deadline = time.monotonic() + timeout
                        elif status == 'DONE' and detail is None and acknowledged:
                            return text
                phase = 'DONE' if acknowledged else 'OK'
                raise TimeoutError(f'Waiting for #{next_id} {phase}; movement unconfirmed, not retried')
            except BaseException as error:
                self.failed = True
                self.last_error = error
                raise
