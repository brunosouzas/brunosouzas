#!/usr/bin/env python3
"""Draw a line of text as SVG outlines, from a TrueType font, with the standard library only.

GitHub shows README images through <img>, where an SVG cannot load a web font,
so the words on the buttons are drawn as paths in the brand's face (Source Sans 3
Bold, a copy of the design system's fonts/SourceSans3-Bold.ttf in fonts/).

Reads what a horizontal line of Latin text needs: cmap (formats 4 and 12), hmtx,
loca/glyf (simple and composite glyphs) and the GPOS pair kerning of the `kern`
feature (PairPos formats 1 and 2, also through Extension lookups). No shaping,
no ligatures: the button labels need none.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ON_CURVE, X_SHORT, Y_SHORT, REPEAT, X_SAME, Y_SAME = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
ARG_WORDS, ARGS_XY, HAS_SCALE, MORE, HAS_XY_SCALE, HAS_2X2 = 0x0001, 0x0002, 0x0008, 0x0020, 0x0040, 0x0080

Point = tuple[float, float, bool]


@dataclass(frozen=True)
class Line:
    """A line of text drawn as one path, in font units with y up, from the pen at (0, 0)."""

    d: str
    advance: int  # font units
    units_per_em: int

    def width(self, size: float) -> float:
        return self.advance * size / self.units_per_em

    def svg(self, x: float, y: float, size: float, fill: str) -> str:
        """A <path> with its baseline starting at (x, y), `size` user units per em."""
        s = size / self.units_per_em
        return f'<path transform="translate({x:g} {y:g}) scale({s:g} {-s:g})" d="{self.d}" fill="{fill}"/>'


class Font:
    def __init__(self, path: Path):
        self.data = path.read_bytes()
        count = self.u16(4)
        self.tables = {
            self.data[12 + 16 * i : 16 + 16 * i].decode("latin-1"): self.u32(12 + 16 * i + 8) for i in range(count)
        }
        head = self.tables["head"]
        self.units_per_em = self.u16(head + 18)
        self.long_loca = self.i16(head + 50) == 1
        self.glyph_count = self.u16(self.tables["maxp"] + 4)
        self.metric_count = self.u16(self.tables["hhea"] + 34)

    # Binary reading -----------------------------------------------------------

    def u16(self, at: int) -> int:
        return struct.unpack_from(">H", self.data, at)[0]

    def i16(self, at: int) -> int:
        return struct.unpack_from(">h", self.data, at)[0]

    def u32(self, at: int) -> int:
        return struct.unpack_from(">I", self.data, at)[0]

    # Characters and metrics ---------------------------------------------------

    @cached_property
    def cmap(self) -> dict[int, int]:
        base = self.tables["cmap"]
        subtables = {}
        for i in range(self.u16(base + 2)):
            platform, encoding, offset = self.u16(base + 4 + 8 * i), self.u16(base + 6 + 8 * i), self.u32(base + 8 + 8 * i)
            subtables[(platform, encoding)] = base + offset
        mapping: dict[int, int] = {}
        if (3, 10) in subtables and self.u16(subtables[(3, 10)]) == 12:
            at = subtables[(3, 10)]
            for g in range(self.u32(at + 12)):
                start, end, glyph = (self.u32(at + 16 + 12 * g + k) for k in (0, 4, 8))
                for code in range(start, end + 1):
                    mapping[code] = glyph + code - start
            return mapping
        at = subtables.get((3, 1)) or subtables[(0, 3)]
        if self.u16(at) != 4:
            raise ValueError("glyphs: no cmap format 4 or 12")
        segments = self.u16(at + 6) // 2
        ends, starts = at + 14, at + 16 + 2 * segments
        deltas, ranges = starts + 2 * segments, starts + 4 * segments
        for s in range(segments):
            start, end = self.u16(starts + 2 * s), self.u16(ends + 2 * s)
            delta, range_offset = self.i16(deltas + 2 * s), self.u16(ranges + 2 * s)
            for code in range(start, min(end, 0xFFFE) + 1):
                if range_offset:
                    glyph = self.u16(ranges + 2 * s + range_offset + 2 * (code - start))
                    glyph = (glyph + delta) & 0xFFFF if glyph else 0
                else:
                    glyph = (code + delta) & 0xFFFF
                mapping[code] = glyph
        return mapping

    def glyph(self, char: str) -> int:
        glyph = self.cmap.get(ord(char), 0)
        if not glyph:
            raise ValueError(f"glyphs: the font has no glyph for {char!r}")
        return glyph

    def advance(self, glyph: int) -> int:
        return self.u16(self.tables["hmtx"] + 4 * min(glyph, self.metric_count - 1))

    # Kerning (GPOS PairPos of the kern feature) -------------------------------

    def _coverage(self, at: int) -> dict[int, int]:
        if self.u16(at) == 1:
            return {self.u16(at + 4 + 2 * i): i for i in range(self.u16(at + 2))}
        index: dict[int, int] = {}
        for r in range(self.u16(at + 2)):
            start, end, first = (self.u16(at + 4 + 6 * r + k) for k in (0, 2, 4))
            for glyph in range(start, end + 1):
                index[glyph] = first + glyph - start
        return index

    def _classes(self, at: int) -> dict[int, int]:
        if self.u16(at) == 1:
            first = self.u16(at + 2)
            return {first + i: self.u16(at + 6 + 2 * i) for i in range(self.u16(at + 4))}
        classes: dict[int, int] = {}
        for r in range(self.u16(at + 2)):
            start, end, cls = (self.u16(at + 4 + 6 * r + k) for k in (0, 2, 4))
            for glyph in range(start, end + 1):
                classes[glyph] = cls
        return classes

    @staticmethod
    def _value_size(fmt: int) -> int:
        return 2 * bin(fmt).count("1")

    def _x_advance(self, at: int, fmt: int) -> int:
        """The XAdvance of a ValueRecord (0 when the format has none)."""
        if not fmt & 0x0004:
            return 0
        return self.i16(at + 2 * bin(fmt & 0x0003).count("1"))

    @cached_property
    def _pair_subtables(self) -> list[int]:
        gpos = self.tables.get("GPOS")
        if gpos is None:
            return []
        features, lookups = gpos + self.u16(gpos + 6), gpos + self.u16(gpos + 8)
        indices: list[int] = []
        for f in range(self.u16(features)):
            if self.data[features + 2 + 6 * f : features + 6 + 6 * f] == b"kern":
                feature = features + self.u16(features + 6 + 6 * f)
                indices += [self.u16(feature + 4 + 2 * i) for i in range(self.u16(feature + 2))]
        subtables = []
        for index in dict.fromkeys(indices):
            lookup = lookups + self.u16(lookups + 2 + 2 * index)
            kind = self.u16(lookup)
            for s in range(self.u16(lookup + 4)):
                sub = lookup + self.u16(lookup + 6 + 2 * s)
                if kind == 9:  # Extension: the real lookup type and a 32-bit offset
                    if self.u16(sub + 2) != 2:
                        continue
                    sub += self.u32(sub + 4)
                elif kind != 2:
                    continue
                subtables.append(sub)
        return subtables

    def kerning(self, left: int, right: int) -> int:
        for sub in self._pair_subtables:
            covered = self._coverage(sub + self.u16(sub + 2)).get(left)
            if covered is None:
                continue
            fmt1, fmt2 = self.u16(sub + 4), self.u16(sub + 6)
            size1, size2 = self._value_size(fmt1), self._value_size(fmt2)
            if self.u16(sub) == 1:
                pairs = sub + self.u16(sub + 10 + 2 * covered)
                for p in range(self.u16(pairs)):
                    record = pairs + 2 + p * (2 + size1 + size2)
                    if self.u16(record) == right:
                        return self._x_advance(record + 2, fmt1)
                continue  # format 1 found no pair: a later subtable may still hold it
            class1 = self._classes(sub + self.u16(sub + 8)).get(left, 0)
            class2 = self._classes(sub + self.u16(sub + 10)).get(right, 0)
            class2_count = self.u16(sub + 14)
            record = sub + 16 + (class1 * class2_count + class2) * (size1 + size2)
            return self._x_advance(record, fmt1)
        return 0

    # Outlines ------------------------------------------------------------------

    def _glyph_range(self, glyph: int) -> tuple[int, int]:
        loca = self.tables["loca"]
        if self.long_loca:
            start, end = self.u32(loca + 4 * glyph), self.u32(loca + 4 * glyph + 4)
        else:
            start, end = 2 * self.u16(loca + 2 * glyph), 2 * self.u16(loca + 2 * glyph + 2)
        return self.tables["glyf"] + start, end - start

    def contours(self, glyph: int) -> list[list[Point]]:
        at, length = self._glyph_range(glyph)
        if length == 0:
            return []
        count = self.i16(at)
        if count < 0:
            return self._composite(at + 10)
        ends = [self.u16(at + 10 + 2 * i) for i in range(count)]
        at += 10 + 2 * count
        at += 2 + self.u16(at)  # skip the instructions
        total = ends[-1] + 1 if ends else 0
        flags: list[int] = []
        while len(flags) < total:
            flag = self.data[at]
            at += 1
            repeat = 0
            if flag & REPEAT:
                repeat = self.data[at]
                at += 1
            flags += [flag] * (repeat + 1)
        xs, at = self._coords(at, flags, X_SHORT, X_SAME)
        ys, at = self._coords(at, flags, Y_SHORT, Y_SAME)
        points = [(x, y, bool(f & ON_CURVE)) for x, y, f in zip(xs, ys, flags)]
        result, start = [], 0
        for end in ends:
            result.append(points[start : end + 1])
            start = end + 1
        return result

    def _coords(self, at: int, flags: list[int], short: int, same: int) -> tuple[list[int], int]:
        values, value = [], 0
        for flag in flags:
            if flag & short:
                step = self.data[at]
                at += 1
                value += step if flag & same else -step
            elif not flag & same:
                value += self.i16(at)
                at += 2
            values.append(value)
        return values, at

    def _composite(self, at: int) -> list[list[Point]]:
        result: list[list[Point]] = []
        while True:
            flags, component = self.u16(at), self.u16(at + 2)
            at += 4
            if flags & ARG_WORDS:
                dx, dy = self.i16(at), self.i16(at + 2)
                at += 4
            else:
                dx, dy = struct.unpack_from(">bb", self.data, at)
                at += 2
            if not flags & ARGS_XY:
                raise ValueError("glyphs: composite glyphs anchored by points are not supported")
            a, b, c, d = 1.0, 0.0, 0.0, 1.0
            f2dot14 = lambda o: self.i16(o) / 16384  # noqa: E731
            if flags & HAS_SCALE:
                a = d = f2dot14(at)
                at += 2
            elif flags & HAS_XY_SCALE:
                a, d = f2dot14(at), f2dot14(at + 2)
                at += 4
            elif flags & HAS_2X2:
                a, b, c, d = (f2dot14(at + k) for k in (0, 2, 4, 6))
                at += 8
            for contour in self.contours(component):
                result.append([(a * x + c * y + dx, b * x + d * y + dy, on) for x, y, on in contour])
            if not flags & MORE:
                return result

    # A line of text ------------------------------------------------------------

    def line(self, text: str) -> Line:
        parts, pen, previous = [], 0, None
        for char in text:
            glyph = self.glyph(char)
            if previous is not None:
                pen += self.kerning(previous, glyph)
            for contour in self.contours(glyph):
                parts.append(contour_path(contour, pen))
            pen += self.advance(glyph)
            previous = glyph
        return Line(d="".join(parts), advance=pen, units_per_em=self.units_per_em)


def _n(value: float) -> str:
    return f"{round(value, 1):g}"


def contour_path(points: list[Point], dx: float = 0) -> str:
    """One closed TrueType contour (quadratic, with implied on-curve midpoints) as path data."""
    if not points:
        return ""
    pts = [(x + dx, y, on) for x, y, on in points]
    first = next((i for i, p in enumerate(pts) if p[2]), None)
    if first is None:  # every point off the curve: start at the midpoint of the first two
        a, b = pts[0], pts[1 % len(pts)]
        pts.insert(0, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, True))
        first = 0
    pts = pts[first:] + pts[:first]
    start = pts[0]
    out = [f"M{_n(start[0])} {_n(start[1])}"]
    control = None
    for x, y, on in pts[1:] + [start]:
        if on:
            out.append(f"Q{_n(control[0])} {_n(control[1])} {_n(x)} {_n(y)}" if control else f"L{_n(x)} {_n(y)}")
            control = None
        else:
            if control:
                mx, my = (control[0] + x) / 2, (control[1] + y) / 2
                out.append(f"Q{_n(control[0])} {_n(control[1])} {_n(mx)} {_n(my)}")
            control = (x, y)
    return "".join(out) + "Z"
