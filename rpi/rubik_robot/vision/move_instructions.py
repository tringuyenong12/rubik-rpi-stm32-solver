"""Manual solution cards with a fixed front/up convention and vector diagrams."""
from dataclasses import dataclass
from html import escape
from math import cos, sin, pi, hypot

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.solver.kociemba_solver import normalize_twophase_solution
from rubik_robot.vision.solve_guide import apply_move, valid_cube


FACE_INFO = {
    'U': ('trên', 'vàng', '#f5d900'), 'R': ('phải', 'xanh lá', '#259b49'),
    'F': ('trước', 'đỏ', '#e7473f'), 'D': ('dưới', 'trắng', '#f4f5f7'),
    'L': ('trái', 'xanh dương', '#3066cc'), 'B': ('sau', 'cam', '#ff982d'),
}
REFERENCE = 'Giữ tâm đỏ F hướng về phía bạn, tâm vàng U ở trên, tâm xanh lá R bên phải.'


@dataclass(frozen=True)
class MoveInstruction:
    token: str

    def __post_init__(self):
        if self.token not in [face+suffix for face in FACE_INFO for suffix in ('', "'", '2')]:
            raise ValueError(f'Invalid move: {self.token}')

    @property
    def face(self):
        return self.token[0]

    @property
    def clockwise(self):
        return not self.token.endswith("'")

    @property
    def degrees(self):
        return 180 if self.token.endswith('2') else 90

    @property
    def title(self):
        name, color, _ = FACE_INFO[self.face]
        return f'{self.token} — mặt {name}, tâm {color}'

    @property
    def description(self):
        name, color, _ = FACE_INFO[self.face]
        direction = 'cùng chiều' if self.clockwise else 'ngược chiều'
        return (f'Nhìn trực diện mặt {name} ({self.face}, tâm {color}): xoay riêng mặt này '
                f'{self.degrees}° {direction} kim đồng hồ. '
                + ('Nước 180° có thể xoay theo cả hai chiều. ' if self.degrees == 180 else '')
                + 'Giữ quy ước F ở trước, U ở trên cho nước tiếp theo.')


class SolutionWalkthrough:
    """Browse instructions without claiming that the physical cube was verified."""
    def __init__(self):
        self.clear()

    def clear(self):
        self.cube, self.solution, self.moves, self.index = '', '', [], 0

    def load(self, cube, solution):
        if not valid_cube(cube):
            raise ValueError('Expected a physically valid scanned cube')
        solution = normalize_twophase_solution(solution)
        moves = [MoveInstruction(token) for token in solution.split()]
        predicted = cube
        for move in moves:
            predicted = apply_move(predicted, move.token)
        if predicted != SOLVED_CUBE:
            raise ValueError('Solution does not solve the scanned cube')
        self.cube, self.solution, self.moves, self.index = cube, solution, moves, 0

    @property
    def current(self):
        return self.moves[self.index] if self.moves else None

    def select(self, index):
        if not 0 <= index < len(self.moves):
            raise IndexError(index)
        self.index = index


def diagram_elements(move):
    """Shared canvas/SVG geometry; circular arrows are viewed from the target face."""
    elements = [('text', [180, 18], {'text': 'Sơ đồ các mặt', 'size': 16})]
    positions = {'U': (1, 0), 'L': (0, 1), 'F': (1, 1), 'R': (2, 1), 'B': (3, 1), 'D': (1, 2)}
    for face, (col, row) in positions.items():
        x, y = 30+col*72, 45+row*72
        selected = face == move.face
        elements.append(('rect', [x, y, x+66, y+66],
                         {'fill': FACE_INFO[face][2], 'stroke': '#101827' if selected else '#8690a0',
                          'width': 4 if selected else 1}))
        elements.append(('text', [x+33, y+33], {'text': face, 'size': 24}))
    elements.append(('text', [174, 290], {'text': 'F hướng về bạn · U ở trên', 'size': 14}))
    elements.append(('text', [560, 18], {'text': f'Nhìn trực diện mặt {move.face}', 'size': 16}))
    x, y, side = 484, 78, 156
    elements.append(('rect', [x, y, x+side, y+side], {'fill': FACE_INFO[move.face][2], 'stroke': '#354052', 'width': 2}))
    for offset in (52, 104):
        elements.append(('line', [x+offset, y, x+offset, y+side], {'fill': '#354052', 'width': 1}))
        elements.append(('line', [x, y+offset, x+side, y+offset], {'fill': '#354052', 'width': 1}))
    elements.append(('text', [x+side/2, y+side/2], {'text': move.face, 'size': 30}))
    # Screen Y grows downwards, so increasing angle is clockwise.
    span = move.degrees*pi/180
    direction = 1 if move.clockwise else -1
    points = []
    for index in range(49):
        angle = -pi/2 + direction*span*index/48
        points.extend((562+112*cos(angle), 156+112*sin(angle)))
    elements.append(('line', points, {'fill': '#111827', 'width': 5, 'arrow': True}))
    elements.append(('text', [562, 300], {'text': f'{move.token} · {move.degrees}° · '
                     + ('cùng chiều' if move.clockwise else 'ngược chiều'), 'size': 16}))
    return elements


def diagram_svg(move):
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 330" role="img" '
              f'aria-label="{escape(move.title, quote=True)}">', '<rect width="740" height="330" fill="#fff"/>']
    for kind, coords, style in diagram_elements(move):
        if kind == 'rect':
            x1, y1, x2, y2 = coords
            pieces.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" '
                          f'fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="{style["width"]}"/>')
        elif kind == 'text':
            pieces.append(f'<text x="{coords[0]}" y="{coords[1]}" text-anchor="middle" dominant-baseline="middle" '
                          f'font-family="Arial,sans-serif" font-size="{style["size"]}" fill="#111827">{escape(style["text"])}</text>')
        else:
            points = ' '.join(f'{coords[i]:.2f},{coords[i+1]:.2f}' for i in range(0, len(coords), 2))
            pieces.append(f'<polyline points="{points}" fill="none" stroke="{style["fill"]}" stroke-width="{style["width"]}"/>')
            if style.get('arrow'):
                x, y, px, py = coords[-2], coords[-1], coords[-4], coords[-3]
                dx, dy = x-px, y-py
                length = hypot(dx, dy)
                dx, dy = dx/length, dy/length
                arrow = [(x, y), (x-17*dx+8*dy, y-17*dy-8*dx), (x-17*dx-8*dy, y-17*dy+8*dx)]
                pieces.append('<polygon fill="#111827" points="'+' '.join(f'{a:.2f},{b:.2f}' for a,b in arrow)+'"/>')
    return ''.join(pieces)+'</svg>'


def export_html(model):
    cards = ''.join(f'<section><h2>Bước {index+1}/{len(model.moves)}: {escape(move.title)}</h2>'
                    f'{diagram_svg(move)}<p>{escape(move.description)}</p></section>'
                    for index, move in enumerate(model.moves))
    return ('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Công thức giải Rubik</title>'
            '<style>body{max-width:900px;margin:32px auto;padding:0 20px;font:17px/1.6 Arial;color:#17202f}'
            'section{border-top:1px solid #ddd;padding:20px 0;break-inside:avoid}svg{width:100%;height:auto}'
            'pre{white-space:pre-wrap;font-size:22px;background:#f0f3f8;padding:20px}</style>'
            f'<h1>Công thức giải Rubik</h1><p>{REFERENCE}</p>'
            '<p>Không đổi hệ quy chiếu giữa các nước. Chiều mũi tên được nhìn thẳng vào chính mặt đang xoay; '
            'với B là nhìn từ phía sau, với D là nhìn từ phía dưới. Dấu ′: ngược chiều; 2: xoay 180°.</p>'
            f'<pre>{escape(model.solution or "Rubik đã ở trạng thái giải")}</pre>' + cards
            + '<p>Đây là hướng dẫn thao tác; camera không xác nhận các bước bạn đã thực hiện.</p></html>')
