"""Mount a separate scramble workspace beside the existing solver client."""

from pathlib import Path
from queue import Queue
from threading import Event, Thread
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from serial.tools import list_ports

from rubik_robot.scramble import create_scramble
from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE
from rubik_robot.transport.scramble_sender import ScrambleSendError, send_scramble


LEVEL_LABELS = {'Easy — 5 moves': 'easy', 'Medium — 12 moves': 'medium', 'Hard — 22 moves': 'hard'}
FACE_COLORS = dict(zip(FACE_ORDER, ('yellow', 'green', 'red', 'white', 'blue', 'orange')))
FACE_POSITIONS = ((1, 0), (2, 1), (1, 1), (1, 2), (0, 1), (3, 1))


class ScrambleWorkspace:
    """Own mode navigation, scramble output and a background UART sender."""

    def __init__(self, root, client):
        """Input: Tk root and existing client module. Output: two selectable workspaces."""
        self.root, self.client = root, client
        self.mode = 'guide'
        self.plan = None
        self.cube_state = SOLVED_CUBE
        self.cube_stickers = []
        self.busy = False
        self.closing = False
        self.closed = False
        self.job = 0
        self.cancel = Event()
        self.events = Queue()
        self.after_id = None
        self.camera_after_id = None
        self.guide_widgets = [(widget, widget.pack_info()) for widget in root.winfo_children()
                              if widget.winfo_manager() == 'pack']
        self.selector = tk.Frame(root)
        self.selector.pack(fill=tk.X, before=client.canvas, padx=10, pady=7)
        self.guide_button = ttk.Button(self.selector, text='Solve Guide', command=lambda: self.select_mode('guide'))
        self.guide_button.pack(side=tk.LEFT, padx=(0, 6))
        self.scramble_button = ttk.Button(self.selector, text='Scramble', command=lambda: self.select_mode('scramble'))
        self.scramble_button.pack(side=tk.LEFT)
        self.frame = ttk.Frame(root, padding=12)
        self.level = tk.StringVar(value=next(iter(LEVEL_LABELS)))
        self.port = tk.StringVar()
        self.baudrate = tk.StringVar(value='115200')
        self.status = tk.StringVar(value='Select a difficulty and generate a scramble.')
        self._build_panel()
        client.canvas.itemconfigure(client.brandom_window, state=tk.HIDDEN)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Destroy>', self._destroyed, add='+')
        self.after_id = root.after(50, self.poll)

    def _build_panel(self):
        """Input: workspace state. Output: difficulty, export, serial and status widgets."""
        ttk.Label(self.frame, text='Scramble', font=('TkDefaultFont', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(self.frame, text='Start with a solved cube. U yellow, F red, R green.').pack(anchor=tk.W, pady=(4, 10))
        row = ttk.Frame(self.frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text='Difficulty').pack(side=tk.LEFT)
        self.level_box = ttk.Combobox(row, textvariable=self.level, values=tuple(LEVEL_LABELS), state='readonly', width=24)
        self.level_box.pack(side=tk.LEFT, padx=8)
        self.generate_button = ttk.Button(row, text='Generate scramble', command=self.generate)
        self.generate_button.pack(side=tk.LEFT)
        ttk.Label(self.frame, text='Difficulty uses scramble length. TURN commands use 450 ms per 90 degrees.').pack(anchor=tk.W, pady=8)
        body = ttk.Frame(self.frame)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)
        self.preview_title = tk.StringVar(value='Start cube — solved')
        ttk.Label(body, textvariable=self.preview_title).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.cube_canvas = tk.Canvas(body, width=330, height=260, highlightthickness=0,
                                     background=self.root.cget('background'))
        self.cube_canvas.grid(row=1, column=0, sticky='nsew', padx=(0, 12))
        self.cube_canvas.bind('<Configure>', self.draw_cube)
        self.output = ScrolledText(body, width=48, height=16, wrap=tk.WORD, font=('TkFixedFont', 10))
        self.output.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.output.configure(state=tk.DISABLED)
        exports = ttk.Frame(self.frame)
        exports.pack(fill=tk.X, pady=8)
        self.copy_button = ttk.Button(exports, text='Copy UART', command=self.copy)
        self.copy_button.pack(side=tk.LEFT)
        self.save_button = ttk.Button(exports, text='Save .txt', command=self.save)
        self.save_button.pack(side=tk.LEFT, padx=8)
        serial_row = ttk.Frame(self.frame)
        serial_row.pack(fill=tk.X)
        ttk.Label(serial_row, text='UART port').pack(side=tk.LEFT)
        self.port_box = ttk.Combobox(serial_row, textvariable=self.port, width=16)
        self.port_box.pack(side=tk.LEFT, padx=8)
        self.refresh_button = ttk.Button(serial_row, text='Refresh ports', command=self.refresh_ports)
        self.refresh_button.pack(side=tk.LEFT)
        ttk.Label(serial_row, text='Baud').pack(side=tk.LEFT, padx=(12, 4))
        self.baud_box = ttk.Combobox(serial_row, textvariable=self.baudrate,
                                    values=('9600', '57600', '115200'), width=10)
        self.baud_box.pack(side=tk.LEFT)
        buttons = ttk.Frame(self.frame)
        buttons.pack(fill=tk.X, pady=8)
        self.send_button = ttk.Button(buttons, text='Send UART', command=self.send)
        self.send_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(buttons, text='Stop after current move', command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=8)
        self.progress = ttk.Progressbar(self.frame, maximum=1)
        self.progress.pack(fill=tk.X, pady=4)
        ttk.Label(self.frame, textvariable=self.status, wraplength=710).pack(anchor=tk.W, pady=5)
        ttk.Label(self.frame, text='Reset the physical cube to solved before every new send.').pack(anchor=tk.W)
        self._set_controls()
        self.draw_cube()

    def draw_cube(self, event=None):
        """Input: target cube and canvas size. Output: its own labeled six-face color net."""
        canvas = self.cube_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1:
            width = int(canvas['width'])
        if height <= 1:
            height = int(canvas['height'])
        cell = max(1, min((width-20) / 12, (height-20) / 9, 52))
        left, top = (width-12*cell) / 2, (height-9*cell) / 2
        canvas.delete('all')
        self.cube_stickers = []
        for index, face in enumerate(FACE_ORDER):
            face_x, face_y = FACE_POSITIONS[index]
            for sticker, color in enumerate(self.cube_state[index*9:index*9+9]):
                x = left + (face_x*3 + sticker % 3)*cell
                y = top + (face_y*3 + sticker // 3)*cell
                item = canvas.create_rectangle(x, y, x+cell, y+cell, fill=FACE_COLORS[color], outline='black')
                self.cube_stickers.append(item)
                if sticker == 4:
                    canvas.create_text(x+cell/2, y+cell/2, text=face, fill='black',
                                       font=('TkDefaultFont', max(9, int(cell*.35))))

    def select_mode(self, mode):
        """Input: guide/scramble choice. Output: switch views and hand camera ownership over."""
        if self.busy or self.closing or mode == self.mode:
            return
        self.mode = mode
        if mode == 'scramble':
            self.client.cancel_guidance()
            self.client.pause_scan()
            self.client.vision2.camera_stop.set()
            for widget, _ in self.guide_widgets:
                widget.pack_forget()
            self.frame.pack(fill=tk.BOTH, expand=True)
            self.refresh_ports()
        else:
            self.frame.pack_forget()
            for widget, options in self.guide_widgets:
                widget.pack(**options)
            self.client.empty()
            self._restart_camera()

    def _restart_camera(self):
        """Input: guide mode. Output: restart the camera after its previous owner exits."""
        self.camera_after_id = None
        if self.mode != 'guide' or self.closed or self.closing:
            return
        vision = self.client.vision2
        options = getattr(vision, 'camera_options', None)
        if options is None:
            return
        owner = getattr(vision, 'camera_thread', None)
        if owner is not None and owner.is_alive():
            vision.camera_stop.set()
            self.camera_after_id = self.root.after(80, self._restart_camera)
            return
        owner = Thread(target=vision.grab_colors, args=options, daemon=True)
        vision.camera_thread = owner
        owner.start()

    def _set_controls(self):
        """Input: send/plan state. Output: prevent overlapping sends and plan edits in flight."""
        ordinary = tk.DISABLED if self.busy or self.closing else tk.NORMAL
        for widget in (self.guide_button, self.scramble_button, self.generate_button,
                       self.refresh_button, self.port_box, self.baud_box):
            widget.configure(state=ordinary)
        self.level_box.configure(state=tk.DISABLED if self.busy else 'readonly')
        available = tk.NORMAL if self.plan is not None and not self.busy and not self.closing else tk.DISABLED
        for widget in (self.send_button, self.copy_button, self.save_button):
            widget.configure(state=available)
        self.stop_button.configure(state=tk.NORMAL if self.busy else tk.DISABLED)

    def generate(self):
        """Input: selected difficulty. Output: solved-cube scramble and corresponding UART frames."""
        if self.busy:
            return
        self.plan = create_scramble(LEVEL_LABELS[self.level.get()])
        self.cube_state = self.plan.cube
        self.preview_title.set('Target cube after scramble')
        self.draw_cube()
        self.output.configure(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.insert(tk.END, 'Scramble moves\n' + ' '.join(self.plan.moves) + '\n\n')
        self.output.insert(tk.END, 'UART commands in execution order\n' + self.plan.uart_text())
        self.output.insert(tk.END, '\nTarget state URFDLB\n' + self.plan.cube + '\n')
        self.output.configure(state=tk.DISABLED)
        self.progress.configure(maximum=len(self.plan.actions), value=0)
        self.status.set(f'Generated {len(self.plan.moves)} moves. Start from a solved cube before sending.')
        self._set_controls()

    def refresh_ports(self):
        """Input: connected devices. Output: refresh available serial port names."""
        try:
            ports = [port.device for port in list_ports.comports()]
        except OSError as error:
            self.status.set(f'Port discovery failed — {error}')
            ports = []
        self.port_box.configure(values=ports)
        if not self.port.get() and ports:
            self.port.set(ports[0])

    def copy(self):
        """Input: current plan. Output: copy its exact UART frames to the clipboard."""
        if self.plan is not None:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.plan.uart_text())
            self.status.set('UART commands copied.')

    def save(self):
        """Input: chosen output file. Output: save the current UART frames as UTF-8 text."""
        if self.plan is None:
            return
        filename = filedialog.asksaveasfilename(parent=self.root, defaultextension='.txt',
                                               filetypes=[('UART text', '*.txt')],
                                               initialfile=f'scramble_{self.plan.level}.txt')
        if filename:
            try:
                Path(filename).write_text(self.plan.uart_text(), encoding='utf-8', newline='\n')
                self.status.set(f'Saved {filename}')
            except OSError as error:
                self.status.set(f'Save failed — {error}')

    def send(self):
        """Input: plan and serial settings. Output: start one background transmission."""
        if self.plan is None or self.busy:
            return
        try:
            baudrate = int(self.baudrate.get())
            port = self.port.get().strip()
            if not port or baudrate <= 0:
                raise ValueError('Choose a valid serial port and baud rate')
        except ValueError as error:
            self.status.set(str(error))
            return
        self.busy = True
        self.cancel.clear()
        self.job += 1
        self.progress.configure(value=0)
        self.status.set('Checking PING, then sending each move and waiting for DONE...')
        self._set_controls()
        Thread(target=self._send_worker, args=(self.job, self.plan, port, baudrate), daemon=True).start()

    def _send_worker(self, job, plan, port, baudrate):
        """Input: fixed plan/port snapshot. Output: progress and final events for the Tk thread."""
        def progress(completed, response):
            """Input: completed command. Output: queue one progress event."""
            self.events.put((job, 'progress', (completed, response)))

        try:
            result = send_scramble(plan, port, baudrate, self.cancel, progress)
            self.events.put((job, 'done', result))
        except ScrambleSendError as error:
            self.events.put((job, 'error', error))
        except Exception as error:
            self.events.put((job, 'error', error))

    def stop(self):
        """Input: stop button. Output: cancel future commands after the in-flight turn finishes."""
        self.cancel.set()
        self.status.set('Waiting for the current move to complete before stopping.')

    def poll(self):
        """Input: worker events. Output: update status/progress exclusively on the Tk thread."""
        self.after_id = None
        if self.closed:
            return
        if self.mode == 'scramble':
            self.client.vision2.camera_stop.set()
        while not self.events.empty():
            job, kind, value = self.events.get_nowait()
            if job != self.job:
                continue
            if kind == 'progress':
                completed, response = value
                self.progress.configure(value=completed)
                self.status.set(f'{completed}/{len(self.plan.moves)} — {response}')
                continue
            self.busy = False
            if kind == 'done':
                text = 'Stopped' if value.cancelled else 'Scramble sent'
                self.status.set(f'{text} — {value.completed}/{len(self.plan.moves)} moves completed.')
            else:
                completed = getattr(value, 'completed', 0)
                self.progress.configure(value=completed)
                uncertainty = ' The last transmitted move is unconfirmed.' if getattr(value, 'uncertain_move', False) else ''
                self.status.set(f'UART failed — {completed} confirmed moves.{uncertainty} {value}. Reset the cube to solved before sending again.')
            self._set_controls()
        if self.closing and not self.busy:
            self.closed = True
            self.client.close_client()
            return
        self.after_id = self.root.after(50, self.poll)

    def _destroyed(self, event):
        """Input: root destruction. Output: release this workspace's pending Tk callbacks."""
        if event.widget is not self.root:
            return
        self.closed = True
        self.cancel.set()
        for callback in (self.after_id, self.camera_after_id):
            if callback is not None:
                self.root.after_cancel(callback)

    def close(self):
        """Input: close-window event. Output: finish/cancel current serial work before closing."""
        if self.busy:
            self.closing = True
            self.stop()
            self._set_controls()
        else:
            self.closed = True
            self.client.close_client()
