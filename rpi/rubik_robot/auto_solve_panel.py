"""Independent Auto Solve workspace mounted beside the two existing workspaces."""

import base64
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from serial.tools import list_ports

from rubik_robot.auto_solve import AutoSolveCancelled, run_auto_solve, scan_commands
from rubik_robot.scramble_panel import FACE_POSITIONS


class AutoSolveWorkspace:
    """Own automatic scanning, UART logs and a separate cube preview."""

    def __init__(self, root, client, workspace):
        """Input: root, existing client and navigation. Output: third selectable workspace."""
        self.root, self.client, self.workspace = root, client, workspace
        self.original_select = workspace.select_mode
        self.original_close = workspace.close
        self.busy = self.closing = self.closed = False
        self.cancel = Event()
        self.events, self.previews = Queue(), Queue(maxsize=1)
        self.job = 0
        self.after_id = None
        self.faces = {}
        self.position_colors = {}
        self.solution_frames = ''
        self.photo = None
        self.port = tk.StringVar()
        self.baud = tk.StringVar(value='115200')
        self.host = tk.StringVar(value='localhost')
        self.server_port = tk.StringVar(value='8080')
        self.status = tk.StringVar(value='Place a scrambled cube in any color orientation, then press Start.')
        self.scan_status = tk.StringVar(value='0/6 faces captured')
        self.frame = ttk.Frame(root, padding=12)
        self.button = ttk.Button(workspace.selector, text='Auto Solve', command=lambda: self.select_mode('auto'))
        self.button.pack(side=tk.LEFT, padx=6)
        self._build()
        # Extend only navigation. Existing guide/scramble callbacks remain unchanged.
        workspace.select_mode = self.select_mode
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Destroy>', self._destroyed, add='+')
        self.after_id = root.after(50, self.poll)

    def _build(self):
        """Input: local state. Output: connection settings, preview, output and Start controls."""
        ttk.Label(self.frame, text='Auto Solve', font=('TkDefaultFont', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(self.frame, text='With the machine in its loading position, place any face up and align the layers. '
                  'Image top toward machine back; image right toward machine right.').pack(anchor=tk.W, pady=5)
        ttk.Label(self.frame, text='Fixed scan positions U → F → D → B → R → L, relative to placement at Start. '
                  'Faces are saved by their detected center colors.').pack(anchor=tk.W)
        row = ttk.Frame(self.frame)
        row.pack(fill=tk.X, pady=8)
        ttk.Label(row, text='UART port').pack(side=tk.LEFT)
        self.port_box = ttk.Combobox(row, textvariable=self.port, width=12)
        self.port_box.pack(side=tk.LEFT, padx=5)
        self.refresh_button = ttk.Button(row, text='Find ports', command=self.refresh_ports)
        self.refresh_button.pack(side=tk.LEFT)
        ttk.Label(row, text='Baud').pack(side=tk.LEFT, padx=(12, 3))
        self.baud_box = ttk.Combobox(row, textvariable=self.baud, values=('115200', '57600', '9600'), width=9)
        self.baud_box.pack(side=tk.LEFT)
        ttk.Label(row, text='Solver host').pack(side=tk.LEFT, padx=(12, 3))
        self.host_box = ttk.Entry(row, textvariable=self.host, width=16)
        self.host_box.pack(side=tk.LEFT)
        ttk.Label(row, text='Port').pack(side=tk.LEFT, padx=(8, 3))
        self.server_box = ttk.Entry(row, textvariable=self.server_port, width=7)
        self.server_box.pack(side=tk.LEFT)
        actions = ttk.Frame(self.frame)
        actions.pack(fill=tk.X)
        self.start_button = ttk.Button(actions, text='Start', command=self.start)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(actions, text='Stop after current operation', command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text='Copy scan route', command=self.copy_scan).pack(side=tk.LEFT)
        self.copy_button = ttk.Button(actions, text='Copy solution UART', command=self.copy_solution, state=tk.DISABLED)
        self.copy_button.pack(side=tk.LEFT, padx=6)
        self.save_button = ttk.Button(actions, text='Save solution .txt', command=self.save_solution, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT)
        ttk.Label(self.frame, textvariable=self.scan_status, font=('TkDefaultFont', 11, 'bold')).pack(anchor=tk.W, pady=(8, 2))
        ttk.Label(self.frame, textvariable=self.status, wraplength=1100).pack(anchor=tk.W, pady=(0, 8))
        body = ttk.Frame(self.frame)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        visuals = ttk.Frame(body)
        visuals.grid(row=0, column=0, sticky='nsew')
        self.preview = ttk.Label(visuals, text='Camera images appear here during capture.', anchor=tk.CENTER)
        self.preview.pack(fill=tk.X)
        self.net = tk.Canvas(visuals, width=480, height=220, highlightthickness=0)
        self.net.pack(fill=tk.BOTH, expand=True)
        self.net.bind('<Configure>', self.draw_cube)
        self.output = ScrolledText(body, width=55, height=24, state=tk.DISABLED)
        self.output.grid(row=0, column=1, sticky='nsew', padx=(12, 0))
        self.log('Fixed scan route (capture gates are controlled by the application):\n' + scan_commands())
        self.log('Capture the initial top face first. Each later SCAN_POSE moves an original machine position '
                 'toward the camera. U restores the Start placement.\n')

    def select_mode(self, mode):
        """Input: requested tab. Output: delegate old tabs or display the independent auto panel."""
        if self.busy or self.closing or self.workspace.busy or self.workspace.closing:
            return
        if mode == self.workspace.mode:
            return
        if mode == 'auto':
            self.original_select('scramble')
            self.workspace.frame.pack_forget()
            self.workspace.mode = 'auto'
            self.frame.pack(fill=tk.BOTH, expand=True)
            self.refresh_ports()
        else:
            self.frame.pack_forget()
            self.original_select(mode)

    def refresh_ports(self):
        """Input: connected serial devices. Output: available ports, preserving manual entries."""
        try:
            ports = [item.device for item in list_ports.comports()]
            self.port_box.configure(values=ports)
            if ports and not self.port.get():
                self.port.set(ports[0])
        except OSError as error:
            self.status.set(f'Port discovery failed: {error}')

    def log(self, text):
        """Input: event text. Output: append to the read-only UART/session log."""
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def draw_cube(self, event=None):
        """Input: captured face dictionary and canvas size. Output: independent 54-cell net."""
        self.net.delete('all')
        size = max(8, min(30, (self.net.winfo_width()-20)//12, (self.net.winfo_height()-12)//9))
        x0 = max(5, (self.net.winfo_width()-12*size)//2)
        for face, (column, row) in zip('URFDLB', FACE_POSITIONS):
            values = self.faces.get(self.position_colors.get(face), ('gray',)*9)
            for index, color in enumerate(values):
                x, y = x0+(column*3+index%3)*size, 5+(row*3+index//3)*size
                self.net.create_rectangle(x, y, x+size, y+size, fill=color, outline='black')
                if index == 4:
                    self.net.create_text(x+size/2, y+size/2, text=face)

    def _controls(self):
        """Input: job/closing state. Output: lock settings and navigation during automatic work."""
        state = tk.DISABLED if self.busy or self.closing else tk.NORMAL
        for widget in (self.start_button, self.port_box, self.baud_box, self.host_box,
                       self.server_box, self.refresh_button, self.workspace.guide_button,
                       self.workspace.scramble_button):
            widget.configure(state=state)
        self.stop_button.configure(state=tk.NORMAL if self.busy and not self.cancel.is_set() else tk.DISABLED)
        ready = tk.NORMAL if self.solution_frames else tk.DISABLED
        self.copy_button.configure(state=ready)
        self.save_button.configure(state=ready)

    def start(self):
        """Input: Start button/settings. Output: one immutable background scan/solve/send session."""
        if self.busy or self.workspace.mode != 'auto' or self.closing:
            return
        try:
            settings = {'port': self.port.get().strip(), 'baud': int(self.baud.get()),
                        'host': self.host.get().strip(), 'server_port': int(self.server_port.get()),
                        'camera': getattr(self.client.vision2, 'camera_options', (1, None, False))}
            if not settings['port'] or not settings['host'] or settings['baud'] <= 0 or not 0 < settings['server_port'] < 65536:
                raise ValueError('Enter UART port, positive baud rate and a valid solver host/port.')
        except ValueError as error:
            self.status.set(str(error))
            return
        self.busy = True
        self.job += 1
        self.cancel.clear()
        self.faces, self.solution_frames, self.position_colors = {}, '', {}
        self.scan_status.set('0/6 faces captured')
        self.status.set('Opening camera and checking the STM32 connection...')
        self.draw_cube()
        self.log('\n=== New Auto Solve session ===\n')
        self._controls()
        Thread(target=self._worker, args=(self.job, settings), daemon=True).start()

    def _worker(self, job, settings):
        """Input: frozen job/settings. Output: queue events after all camera/UART resources close."""
        def emit(kind, value):
            """Input: controller event. Output: tagged event for the Tk thread."""
            self.events.put((job, kind, value))

        def preview(png):
            """Input: PNG frame. Output: replace queued preview to keep memory bounded."""
            try:
                self.previews.get_nowait()
            except Empty:
                pass
            self.previews.put_nowait((job, png))

        try:
            run_auto_solve(settings, self.cancel, emit, preview)
            emit('finished', 'Auto Solve complete. Camera verified six solid faces in the starting orientation.')
        except AutoSolveCancelled as error:
            emit('finished', str(error))
        except Exception as error:
            emit('finished', f'Stopped: {error}. Check the cube and machine. Restore the arms to '
                 'the loading position before starting a new scan.')

    def stop(self):
        """Input: stop request. Output: block subsequent commands while current operation finishes."""
        self.cancel.set()
        self.status.set('Stopping after the current operation. No automatic retries.')
        self._controls()

    def poll(self):
        """Input: worker queues. Output: render updates on Tk and finish deferred close."""
        self.after_id = None
        if self.closed:
            return
        while True:
            try:
                job, kind, value = self.events.get_nowait()
            except Empty:
                break
            if job != self.job:
                continue
            if kind == 'orientation':
                self.position_colors = value
                self.log('Observed centers: ' + ', '.join(f'{face}={color}' for face, color in value.items()) + '\n')
                self.draw_cube()
            elif kind == 'route':
                self.log('Fixed scan commands after the first capture:\n' + value)
            elif kind == 'face':
                self.faces = value
                self.scan_status.set(f'{len(value)}/6 faces captured')
                self.draw_cube()
            elif kind == 'move':
                index, total, self.faces = value
                self.draw_cube()
                self.log(f'Confirmed solution step {index}/{total}\n')
            elif kind == 'solution':
                self.solution_frames = value['uart']
                self.log('\nCube URFDLB in machine coordinates\n' + value['cube']
                         + '\nSolution in machine coordinates\n' + (value['solution'] or '<already solved>')
                         + '\nSolution UART\n' + self.solution_frames)
                self._controls()
            else:
                if kind == 'command':
                    self.log('TX ' + value + '\n')
                else:
                    self.status.set(value)
                    self.log(value + '\n')
                if kind == 'scan_complete':
                    self.scan_status.set('6/6 faces captured — checking cube')
                if kind == 'finished':
                    self.busy = False
                    self._controls()
        try:
            job, png = self.previews.get_nowait()
            if job == self.job:
                self.photo = tk.PhotoImage(data=base64.b64encode(png).decode('ascii'), format='png')
                self.preview.configure(image=self.photo, text='')
        except Empty:
            pass
        self.button.configure(state=tk.DISABLED if self.busy or self.closing or self.workspace.busy else tk.NORMAL)
        if self.closing and not self.busy:
            self.original_close()
            return
        self.after_id = self.root.after(50, self.poll)

    def copy_scan(self):
        """Input: fixed route. Output: copy pose commands with required capture gates noted in UI."""
        self.root.clipboard_clear()
        self.root.clipboard_append(scan_commands())

    def copy_solution(self):
        """Input: verified solver plan. Output: RUBIK MOVE command bodies on the clipboard."""
        if self.solution_frames:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.solution_frames)

    def save_solution(self):
        """Input: chosen file. Output: save verified solution frames, including an empty solved plan."""
        filename = filedialog.asksaveasfilename(parent=self.root, defaultextension='.txt',
                                               initialfile='auto_solution.txt', filetypes=[('UART text', '*.txt')])
        if filename:
            try:
                Path(filename).write_text(self.solution_frames, encoding='utf-8', newline='\n')
            except OSError as error:
                self.status.set(f'Save failed: {error}')

    def close(self):
        """Input: window-close request. Output: close after current automatic operation completes."""
        if self.busy:
            self.closing = True
            self.stop()
        else:
            self.original_close()

    def _destroyed(self, event):
        """Input: root destruction. Output: cancel worker and pending panel callbacks."""
        if event.widget is self.root:
            self.closed = True
            self.cancel.set()
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
