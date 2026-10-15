"""The README images must render on GitHub, which shows them through <img>."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_assets as ba  # noqa: E402

COVER = (ba.SOURCE / "home-banner.svg").read_text(encoding="utf-8")  # any site illustration
SVG = "{http://www.w3.org/2000/svg}"


def article_cards() -> dict[str, str]:
    title = "From a one-line request to a living spec: spec-driven development in practice"
    return {
        f"card{suffix}": ba.article_card(COVER, title, "10 Oct, 2026", theme)
        for suffix, theme in ba.THEMES
    }


class Problems(unittest.TestCase):
    def test_accepts_a_plain_drawing(self):
        self.assertEqual(ba.problems('<svg><rect fill="#fff"/></svg>'), [])

    def test_names_each_construct_that_would_not_render(self):
        for svg in (
            '<svg><use href="#a"/></svg>',
            "<svg><style>rect{}</style></svg>",
            "<svg><script>x()</script></svg>",
            '<svg><image x="0"/></svg>',
            "<svg><foreignObject/></svg>",
            '<svg><rect fill="currentColor"/></svg>',
            '<svg><rect filter="url(#b)"/></svg>',
            "<svg><linearGradient/></svg>",
            '<svg><rect style="fill:red"/></svg>',
        ):
            with self.subTest(svg=svg):
                self.assertTrue(ba.problems(svg))


class TitleLines(unittest.TestCase):
    def test_wraps_on_words_within_the_card(self):
        lines = ba.title_lines("What Remains for Software Developers When AI Writes Code?")
        self.assertEqual(lines, ["What Remains for Software", "Developers When AI Writes Code?"])
        self.assertTrue(all(len(line) <= ba.TITLE_CHARS for line in lines))

    def test_cuts_a_long_title_at_three_lines_with_an_ellipsis(self):
        lines = ba.title_lines(" ".join(["integration"] * 20))
        self.assertEqual(len(lines), ba.TITLE_LINES)
        self.assertTrue(lines[-1].endswith("…"))
        self.assertTrue(all(len(line) <= ba.TITLE_CHARS for line in lines))


class GeneratedSvgs(unittest.TestCase):
    def setUp(self):
        self.files = {**ba.generated(), **article_cards()}

    def test_every_readme_image_exists(self):
        readme = (ba.ROOT / "README.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r'(?:src|srcset)="(assets/[^"]+\.svg)"', readme))
        self.assertTrue(referenced)
        self.assertEqual({p for p in referenced if not (ba.ROOT / p).is_file()}, set())

    def test_parse_as_xml(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                ET.fromstring(svg)

    def test_are_self_contained(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                self.assertEqual(ba.problems(svg), [])

    def test_are_accessible(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                root = ET.fromstring(svg)
                self.assertEqual(root.get("role"), "img")
                ids = root.get("aria-labelledby", "").split()
                self.assertEqual(len(ids), 2)
                title, desc = root.find(f"{SVG}title"), root.find(f"{SVG}desc")
                assert title is not None and desc is not None
                self.assertEqual([title.get("id"), desc.get("id")], ids)
                self.assertTrue(title.text and desc.text)

    def test_article_card_shows_the_title_date_and_cover(self):
        root = ET.fromstring(article_cards()["card"])
        texts = [t.text for t in root.findall(f"{SVG}text")]  # the card's own text, not the cover's
        self.assertIn("10 Oct, 2026", texts)
        self.assertEqual(texts[0], "From a one-line request to a")
        desc = root.find(f"{SVG}desc")
        assert desc is not None and desc.text
        self.assertIn("published 10 Oct, 2026. Cover: Illustration. On the left", desc.text)
        self.assertEqual(len([s for s in root.iter(f"{SVG}svg")]), 2)  # the card and the nested cover

    def test_match_the_committed_files(self):
        for name, svg in ba.generated().items():
            with self.subTest(name):
                self.assertEqual((ba.OUTPUT / name).read_text(encoding="utf-8"), svg)


if __name__ == "__main__":
    unittest.main()
