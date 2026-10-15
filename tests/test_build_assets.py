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
ARTICLES = ba.OUTPUT / "articles"
README = (ba.ROOT / "README.md").read_text(encoding="utf-8")


def thumbnails() -> dict[str, str]:
    return {"thumbnail": ba.thumbnail(COVER, "Spec-driven development in practice")}


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


class GeneratedSvgs(unittest.TestCase):
    def setUp(self):
        committed = {f"articles/{p.name}": p.read_text(encoding="utf-8") for p in ARTICLES.glob("*.svg")}
        self.files = {**ba.generated(), **thumbnails(), **committed}

    def test_every_readme_image_exists(self):
        referenced = set(re.findall(r'(?:src|srcset)="(assets/[^"]+\.svg)"', README))
        self.assertTrue(referenced)
        self.assertEqual({p for p in referenced if not (ba.ROOT / p).is_file()}, set())

    def test_every_committed_card_is_shown(self):
        referenced = set(re.findall(r'(?:src|srcset)="assets/articles/([^"]+\.svg)"', README))
        self.assertEqual({p.name for p in ARTICLES.glob("*.svg")}, referenced)

    def test_assets_top_level_is_exactly_what_the_script_draws(self):
        self.assertEqual({p.name for p in ba.OUTPUT.glob("*.svg")}, set(ba.generated()))

    def test_header_is_not_a_link(self):
        self.assertRegex(README, r'<picture><img src="assets/header\.svg"')
        self.assertNotRegex(README, r'<a [^>]*>\s*(<picture>)?\s*<img src="assets/header\.svg"')

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

    def test_thumbnail_is_the_cover_with_rounded_corners(self):
        root = ET.fromstring(thumbnails()["thumbnail"])
        self.assertEqual(root.get("viewBox"), "0 0 800 420")
        title, desc = root.find(f"{SVG}title"), root.find(f"{SVG}desc")
        assert title is not None and desc is not None and desc.text
        self.assertEqual(title.text, "Cover: Spec-driven development in practice")
        self.assertTrue(desc.text.startswith("Illustration. On the left"))  # the cover's own description
        clip = root.find(f"{SVG}defs/{SVG}clipPath/{SVG}rect")
        assert clip is not None
        self.assertEqual(clip.get("rx"), str(ba.THUMB_RADIUS))
        self.assertEqual(len(list(root.iter(f"{SVG}svg"))), 2)  # the frame and the nested cover

    def test_match_the_committed_files(self):
        for name, svg in ba.generated().items():
            with self.subTest(name):
                self.assertEqual((ba.OUTPUT / name).read_text(encoding="utf-8"), svg)


if __name__ == "__main__":
    unittest.main()
