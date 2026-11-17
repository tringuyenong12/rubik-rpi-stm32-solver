"""Formula and illustrated move cards, independent of the camera preview."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from rubik_robot.vision.move_instructions import (
    SolutionWalkthrough, REFERENCE, diagram_elements, export_html,
)


class SolutionPanel:
    def __init__(self, root):
        self.root = root
        self.model = SolutionWalkthrough()
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.title('Công thức và quy ước xoay Rubik')
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)
        self.window.resizable(False, False)
        body = ttk.Frame(self.window, padding=16)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text='Công thức giải Rubik', font=('TkDefaultFont', 17, 'bold')).pack(anchor=tk.W)
        ttk.Label(body, text=REFERENCE, wraplength=740).pack(anchor=tk.W, pady=(6, 4))
        self.formula = tk.Text(body, height=3, width=78, wrap=tk.WORD, font=('Consolas', 14))
        self.formula.pack(fill=tk.X, pady=6)
        self.formula.tag_configure('current', background='#ffe098', foreground='#111827')
        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=4)
        ttk.Button(actions, text='Sao chép công thức', command=self.copy).pack(side=tk.LEFT)
        ttk.Button(actions, text='Lưu hướng dẫn .html', command=self.save).pack(side=tk.LEFT, padx=8)
        self.heading = tk.StringVar()
        ttk.Label(body, textvariable=self.heading, font=('TkDefaultFont', 14, 'bold')).pack(anchor=tk.W, pady=(10, 2))
        self.canvas = tk.Canvas(body, width=740, height=330, background='white', highlightthickness=0)
        self.canvas.pack()
        self.description = tk.StringVar()
        ttk.Label(body, textvariable=self.description, wraplength=740).pack(anchor=tk.W, pady=6)
        ttk.Label(body, text='Hình phóng to dùng để đọc chiều xoay, không đổi mặt F. B: nhìn từ sau; D: nhìn từ dưới.',
                  wraplength=740).pack(anchor=tk.W)
        navigation = ttk.Frame(body)
        navigation.pack(fill=tk.X, pady=(12, 4))
        self.previous = ttk.Button(navigation, text='← Bước trước', command=lambda: self.step(-1))
        self.previous.pack(side=tk.LEFT)
        self.next = ttk.Button(navigation, text='Bước tiếp →', command=lambda: self.step(1))
        self.next.pack(side=tk.LEFT, padx=8)
        ttk.Label(body, text='Bạn tự chuyển bước. Camera chỉ nhận diện màu, không xác nhận thao tác giải.',
                  wraplength=740).pack(anchor=tk.W)
        self.window.bind('<Left>', lambda event: self.step(-1))
        self.window.bind('<Right>', lambda event: self.step(1))

    def clear(self):
        self.model.clear()
        self.window.withdraw()

    def show(self, cube, solution):
        self.model.load(cube, solution)
        self.render()
        self.reopen()

    def reopen(self):
        if self.model.cube:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

    def step(self, delta):
        target = self.model.index + delta
        if 0 <= target < len(self.model.moves):
            self.model.select(target)
            self.render()

    def render(self):
        self.formula.configure(state=tk.NORMAL)
        self.formula.delete('1.0', tk.END)
        self.formula.insert('1.0', self.model.solution or 'Rubik đã ở trạng thái giải.')
        start = sum(len(move.token)+1 for move in self.model.moves[:self.model.index])
        if self.model.current:
            self.formula.tag_add('current', f'1.0+{start}c', f'1.0+{start+len(self.model.current.token)}c')
            self.formula.see(f'1.0+{start}c')
        self.formula.configure(state=tk.DISABLED)
        self.previous.configure(state=tk.NORMAL if self.model.index > 0 else tk.DISABLED)
        self.next.configure(state=tk.NORMAL if self.model.index+1 < len(self.model.moves) else tk.DISABLED)
        self.canvas.delete('all')
        move = self.model.current
        if move is None:
            self.heading.set('Không cần thao tác xoay')
            self.description.set('Trạng thái Rubik đã quét là trạng thái đã giải.')
            return
        self.heading.set(f'Bước {self.model.index+1}/{len(self.model.moves)}: {move.title}')
        self.description.set(move.description)
        for kind, coords, style in diagram_elements(move):
            if kind == 'rect':
                self.canvas.create_rectangle(*coords, fill=style['fill'], outline=style['stroke'], width=style['width'])
            elif kind == 'text':
                self.canvas.create_text(*coords, text=style['text'], font=('TkDefaultFont', style['size'], 'bold'), fill='#111827')
            else:
                self.canvas.create_line(*coords, fill=style['fill'], width=style['width'],
                                        arrow=tk.LAST if style.get('arrow') else tk.NONE, arrowshape=(17, 20, 8))

    def copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.model.solution)

    def save(self):
        filename = filedialog.asksaveasfilename(parent=self.window, title='Lưu công thức và hình minh họa',
                                              defaultextension='.html', filetypes=[('HTML', '*.html')])
        if filename:
            try:
                Path(filename).write_text(export_html(self.model), encoding='utf-8')
            except OSError as error:
                messagebox.showerror('Không lưu được hướng dẫn', str(error), parent=self.window)
