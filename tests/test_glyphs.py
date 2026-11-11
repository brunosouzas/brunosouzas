"""The button words are outlines drawn from the brand's TrueType face."""

import struct
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

    def test_all_off_curve_contour_starts_between_the_last_and_the_first_point(self):
        square = [(0, 0, False), (10, 0, False), (10, 10, False), (0, 10, False)]
        self.assertEqual(glyphs.contour_path(square), "M0 5Q0 0 5 0Q10 0 10 5Q10 10 5 10Q0 10 0 5Z")

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

    def test_composite_glyph_places_its_components(self):
        # 'i' is dotlessi plus the dot (uni0307) moved 138 units right (read with fontTools).
        dotless, dot = FONT.contours(FONT.glyph("\u0131")), FONT.contours(FONT.glyph("\u0307"))
        moved = [[(x + 138, y, on) for x, y, on in contour] for contour in dot]
        i = FONT.contours(FONT.glyph("i"))
        self.assertEqual(i, dotless + moved)
        self.assertEqual([len(c) for c in i], [4, 12])

    def test_refuses_a_composite_glyph_that_contains_itself(self):
        font = object.__new__(glyphs.Font)
        font.data = struct.pack(">5hHHbb", -1, 0, 0, 0, 0, glyphs.ARGS_XY, 0, 0, 0)  # glyph 0 = glyph 0 at (0, 0)
        font._glyph_range = lambda glyph: (0, len(font.data))
        with self.assertRaisesRegex(ValueError, "nested deeper"):
            font.contours(0)

    def test_kerns_by_class(self):
        # A V is kerned by a class-based subtable (PairPos format 2: A in class 0, V in class 15), -18 per fontTools.
        self.assertEqual(FONT.kerning(FONT.glyph("A"), FONT.glyph("V")), -18)

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
