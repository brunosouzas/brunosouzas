"""The button words are outlines drawn from the brand's TrueType face."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_assets as ba  # noqa: E402
import glyphs  # noqa: E402

FONT = glyphs.Font(ba.FONT_FILE)


class ContourPath(unittest.TestCase):
    def test_straight_contour(self):
        square = [(0, 0, True), (10, 0, True), (10, 10, True)]
        self.assertEqual(glyphs.contour_path(square), "M0 0L10 0L10 10L0 0Z")

    def test_implied_point_between_two_off_curve_points(self):
        contour = [(0, 0, True), (0, 10, False), (10, 10, False)]
        self.assertEqual(glyphs.contour_path(contour), "M0 0Q0 10 5 10Q10 10 0 0Z")

    def test_shift_by_the_pen(self):
        self.assertEqual(glyphs.contour_path([(0, 0, True), (1, 0, True)], dx=100), "M100 0L101 0L100 0Z")


class Font(unittest.TestCase):
    def test_reads_the_face(self):
        self.assertEqual(FONT.units_per_em, 1000)
        self.assertGreater(len(FONT.contours(FONT.glyph("o"))), 1)  # an outer and an inner contour

    def test_kerns_pairs(self):
        t, o = FONT.glyph("T"), FONT.glyph("o")
        self.assertLess(FONT.kerning(t, o), 0)
        self.assertEqual(FONT.line("To").advance, FONT.advance(t) + FONT.advance(o) + FONT.kerning(t, o))

    def test_space_has_width_and_no_outline(self):
        line = FONT.line(" ")
        self.assertGreater(line.advance, 0)
        self.assertEqual(line.d, "")

    def test_refuses_a_character_it_cannot_draw(self):
        with self.assertRaises(ValueError):
            FONT.line("\u4e2d")

    def test_line_as_svg(self):
        line = FONT.line("Email")
        self.assertAlmostEqual(line.width(17), line.advance * 17 / 1000)
        self.assertTrue(line.svg(46, 27.61, 17, "#121212").startswith('<path transform="translate(46 27.61) scale(0.017 -0.017)" d="M'))


if __name__ == "__main__":
    unittest.main()
