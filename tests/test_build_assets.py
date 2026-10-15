"""The generated SVGs must render on GitHub, which shows README images through <img>."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_assets as ba  # noqa: E402

FORBIDDEN = {
    "an external or internal link": re.compile(r"\bhref="),
    "a <style> block": re.compile(r"<style\b"),
    "a <script>": re.compile(r"<script\b"),
    "an embedded image": re.compile(r"<image\b"),
    "currentColor": re.compile(r"currentColor"),
    "a blur or filter": re.compile(r"\bfilter\b|Gradient"),
    "inline CSS": re.compile(r'\bstyle="|\bclass="'),
}


def generated() -> dict[str, str]:
    files = {"header.svg": ba.header()}
    for dark, theme in ((False, ba.LIGHT), (True, ba.DARK)):
        suffix = "-dark" if dark else ""
        for item in ba.TOPICS:
            files[f"topic-{item.slug}{suffix}.svg"] = ba.topic(item, theme, dark)
        for item in ba.LINKS:
            files[f"link-{item.slug}{suffix}.svg"] = ba.link(item, theme, dark)
    return files


class GeneratedSvgs(unittest.TestCase):
    def setUp(self):
        self.files = generated()

    def test_every_readme_image_is_generated(self):
        readme = (ba.ROOT / "README.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r'(?:src|srcset)="assets/([^"/]+\.svg)"', readme))
        self.assertTrue(referenced)
        self.assertEqual(referenced - set(self.files), set())

    def test_parse_as_xml(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                ET.fromstring(svg)

    def test_are_self_contained(self):
        for name, svg in self.files.items():
            for what, pattern in FORBIDDEN.items():
                with self.subTest(name, rule=what):
                    self.assertIsNone(pattern.search(svg), f"{name} has {what}")

    def test_are_accessible(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                root = ET.fromstring(svg)
                self.assertEqual(root.get("role"), "img")
                ids = root.get("aria-labelledby", "").split()
                self.assertEqual(len(ids), 2)
                ns = "{http://www.w3.org/2000/svg}"
                title, desc = root.find(f"{ns}title"), root.find(f"{ns}desc")
                assert title is not None and desc is not None
                self.assertEqual([title.get("id"), desc.get("id")], ids)
                self.assertTrue(title.text and desc.text)

    def test_match_the_committed_files(self):
        for name, svg in self.files.items():
            with self.subTest(name):
                self.assertEqual((ba.OUTPUT / name).read_text(encoding="utf-8"), svg)


if __name__ == "__main__":
    unittest.main()
