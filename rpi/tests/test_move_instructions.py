"""Validate all move conventions, manual navigation and portable vector output."""
import unittest
import xml.etree.ElementTree as ET

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.vision.solve_guide import apply_move
from rubik_robot.vision.move_instructions import (
    FACE_INFO, MoveInstruction, SolutionWalkthrough, diagram_elements, diagram_svg, export_html,
)


class TestMoveInstructions(unittest.TestCase):
    def test_all_eighteen_moves_have_face_diagrams_and_correct_turn_conventions(self):
        for face in FACE_INFO:
            for suffix in ('', "'", '2'):
                with self.subTest(move=face+suffix):
                    move = MoveInstruction(face+suffix)
                    self.assertEqual(move.face, face)
                    self.assertEqual(move.degrees, 180 if suffix == '2' else 90)
                    self.assertEqual(move.clockwise, suffix != "'")
                    self.assertIn('Nhìn trực diện', move.description)
                    root = ET.fromstring(diagram_svg(move))
                    self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
                    arrow = next(coords for kind, coords, style in diagram_elements(move) if style.get('arrow'))
                    self.assertEqual(arrow[2] > arrow[0], move.clockwise)
                    if move.degrees == 180:
                        self.assertAlmostEqual(arrow[-2], 562)
                        self.assertAlmostEqual(arrow[-1], 268)
                    else:
                        self.assertAlmostEqual(arrow[-2], 674 if move.clockwise else 450)
                        self.assertAlmostEqual(arrow[-1], 156)

    def test_half_turn_remains_one_step_and_browsing_keeps_scanned_cube(self):
        cube = apply_move(apply_move(SOLVED_CUBE, 'R'), 'U2')
        model = SolutionWalkthrough()
        model.load(cube, "U2 R'")
        self.assertEqual(len(model.moves), 2)
        self.assertEqual(model.current.token, 'U2')
        model.select(1)
        self.assertEqual(model.current.token, "R'")
        self.assertEqual(model.cube, cube)
        model.select(0)
        self.assertEqual(model.current.degrees, 180)
        with self.assertRaises(IndexError):
            model.select(2)

    def test_invalid_solution_and_invalid_tokens_are_rejected(self):
        model = SolutionWalkthrough()
        with self.assertRaises(ValueError):
            model.load(apply_move(SOLVED_CUBE, 'R'), 'U')
        with self.assertRaises(ValueError):
            MoveInstruction('X')
        self.assertEqual(model.moves, [])

    def test_export_embeds_each_step_and_fixed_orientation_without_external_assets(self):
        model = SolutionWalkthrough()
        model.load(apply_move(SOLVED_CUBE, 'F'), "F'")
        result = export_html(model)
        self.assertIn('F hướng về phía bạn', result)
        self.assertIn('Bước 1/1', result)
        self.assertIn('nhìn từ phía sau', result)
        self.assertIn('<svg', result)
        self.assertNotIn('<script', result)
        self.assertNotIn('<img src=', result)
        self.assertIn('camera không xác nhận', result)

    def test_solved_cube_has_no_unnecessary_steps(self):
        model = SolutionWalkthrough()
        model.load(SOLVED_CUBE, '')
        self.assertIsNone(model.current)
        self.assertIn('Rubik đã ở trạng thái giải', export_html(model))
        model.clear()
        self.assertEqual(model.cube, '')


if __name__ == '__main__':
    unittest.main()
