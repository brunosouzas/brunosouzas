"""The README images must render on GitHub, which shows them through <img>."""

import html
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_assets as ba  # noqa: E402

COVER = (ba.SOURCE / "og-en.svg").read_text(encoding="utf-8")  # any site illustration, with an embedded font
FONT_FACE = "@font-face{font-family:'Source Sans 3';font-weight:550 799;src:url(data:font/ttf;base64,AAEAAA==) format('truetype')}"
SVG = "{http://www.w3.org/2000/svg}"
ARTICLES = ba.OUTPUT / "articles"
DESIGN_SYSTEM = ba.OUTPUT / "design-system"  # the design system's link icons, copied as its cover command writes them
README = (ba.ROOT / "README.md").read_text(encoding="utf-8")
FIND_ME = README[README.index("### Find me"):]
# The Find me row, in order: where each icon links, its file stem in assets/design-system/ and its accessible name.
FIND_ME_LINKS = [
    ("https://brunosouzas.com/", "link-brunosouzas", "brunosouzas.com"),
    ("https://www.linkedin.com/in/brunosouzas", "link-linkedin", "LinkedIn"),
    ("mailto:brunosouzas@gmail.com", "link-email", "Email"),
]


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
            "<svg><style>@font-face{src:url(https://example.com/a.ttf)}</style></svg>",
            "<svg><style>@import url(data:font/ttf;base64,AA==);</style></svg>",
            f"<svg><style>{FONT_FACE}rect{{fill:red}}</style></svg>",
            "<svg><style>@font-face{font-family:x}</style></svg>",
            '<svg><rect fill="url(https://example.com/p)"/></svg>',
        ):
            with self.subTest(svg=svg):
                self.assertTrue(ba.problems(svg))


    def test_refuses_a_remote_font_beside_an_embedded_one(self):
        embedded = "url(data:font/ttf;base64,AA==)"
        for remote in ("URL(https://e.com/a.ttf)", "Url( 'https://e.com/a.ttf' )", "url(//e.com/a.ttf)"):
            with self.subTest(remote=remote):
                svg = f"<svg><style>@font-face{{font-family:x;src:{embedded},{remote}}}</style></svg>"
                self.assertIn("a <style> block other than embedded @font-face fonts", ba.problems(svg))
                self.assertIn("an external url()", ba.problems(svg))

    def test_refuses_a_css_escape_in_a_style(self):
        svg = "<svg><style>@font-face{src:url(data:font/ttf;base64,AA==),u\\72l(https://e.com/a.ttf)}</style></svg>"
        self.assertIn("a CSS escape", ba.problems(svg))
        self.assertIn("a <style> block other than embedded @font-face fonts", ba.problems(svg))

    def test_refuses_an_external_url_in_any_case_outside_a_style(self):
        for value in ("URL(https://e.com/p)", "url( //e.com/p)", "url(data:image/png;base64,AA==)"):
            with self.subTest(value=value):
                self.assertEqual(ba.problems(f'<svg><rect fill="{value}"/></svg>'), ["an external url()"])

    def test_accepts_a_fragment_url_in_any_spacing_and_case(self):
        for value in ("url(#a)", "url( #a)", "URL('#a')"):
            with self.subTest(value=value):
                self.assertEqual(ba.problems(f'<svg><rect clip-path="{value}"/></svg>'), [])

    def test_sees_through_spacing_prefixes_and_quotes(self):
        for svg, what in (
            ('<svg><use href ="https://e.com/a"/></svg>', "an external or internal link"),
            ('<svg xmlns:x="http://www.w3.org/1999/xlink"><use x:href="#a"/></svg>', "an external or internal link"),
            ('<svg xmlns:s="http://www.w3.org/2000/svg"><s:script>x()</s:script></svg>', "a <script>"),
            ('<svg xmlns:s="urn:x"><s:foreignObject/></svg>', "an embedded image or object"),
            ('<svg onload="x()"><rect/></svg>', "an event handler"),
            ("<svg><rect onClick='x()'/></svg>", "an event handler"),
            ("<svg><rect style='fill:red'/></svg>", "inline CSS"),
            ('<?xml-stylesheet href="https://e.com/a.css"?><svg/>', "an external or internal link"),
        ):
            with self.subTest(svg=svg):
                self.assertIn(what, ba.problems(svg))

    def test_refuses_markup_that_does_not_parse(self):
        self.assertEqual(ba.problems("<svg><s:script>x()</s:script></svg>"), ["not well-formed XML"])

    def test_accepts_fonts_embedded_as_the_design_system_writes_them(self):
        # The site's v2 covers carry a per-image subset of Source Sans 3 (design system ADR 0008).
        self.assertEqual(ba.problems(f'<svg><style>{FONT_FACE}</style><rect clip-path="url(#c)"/></svg>'), [])


class GeneratedSvgs(unittest.TestCase):
    def setUp(self):
        committed = {
            f"{folder.name}/{p.name}": p.read_text(encoding="utf-8")
            for folder in (ARTICLES, DESIGN_SYSTEM)
            for p in folder.glob("*.svg")
        }
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

    def test_script_draws_the_header_and_the_all_articles_button_only(self):
        self.assertEqual(set(ba.generated()), {"header.svg", "link-articles.svg", "link-articles-dark.svg"})

    def test_site_copies_are_only_what_the_script_reads(self):
        self.assertEqual({p.name for p in ba.SOURCE.iterdir()}, {ba.HEADER_SOURCE})

    def test_header_alt_carries_the_name_and_the_slogan(self):
        alt = re.search(r'<img src="assets/header\.svg"[^>]* alt="([^"]+)"', README)
        assert alt is not None
        self.assertTrue(html.unescape(alt.group(1)).startswith(
            'Bruno Souza, brunosouzas.com: "Code that runs for the problem you have."'
        ))

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
        self.assertTrue(desc.text.startswith("The slogan"))  # the cover's own description
        clip = root.find(f"{SVG}defs/{SVG}clipPath/{SVG}rect")
        assert clip is not None
        self.assertEqual(clip.get("rx"), str(ba.THUMB_RADIUS))
        self.assertEqual(len(list(root.iter(f"{SVG}svg"))), 2)  # the frame and the nested cover

    def test_header_is_the_site_share_image(self):
        root = ET.fromstring(ba.header())
        image = ET.parse(ba.SOURCE / ba.HEADER_SOURCE).getroot()
        self.assertEqual(ba.HEADER_SOURCE, "og-en.svg")
        self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")), ("1200", "630", "0 0 1200 630"))
        self.assertEqual(root.find(f"{SVG}desc").text, image.find(f"{SVG}desc").text)
        self.assertEqual(root.get("font-family"), image.get("font-family"))
        self.assertEqual(len(list(root.iter())), len(list(image.iter())))  # same drawing, same title and desc
        self.assertEqual(root.find(f"{SVG}style").text, image.find(f"{SVG}style").text)  # the embedded slogan face
        self.assertEqual([t.text for t in root.iter(f"{SVG}text")], ["Code that runs", "for the problem", "you have."])
        self.assertEqual(ba.problems(ba.header()), [])

    def test_buttons_draw_their_words_as_outlines(self):
        for name, svg in ba.generated().items():
            if name.startswith("link-"):
                with self.subTest(name):
                    root = ET.fromstring(svg)
                    self.assertIsNone(root.find(f".//{SVG}text"))
                    self.assertIsNone(root.get("font-family"))  # nothing left to inherit it
                    self.assertEqual(root.get("height"), str(ba.LINK_H))
                    self.assertNotIn("<style", svg)

    def test_buttons_use_the_v2_palette_only(self):
        old = ("#0A1033", "#14215A", "#1C2D74", "#FFD25A", "#3DDC84", "#4C5CB8")
        for name, svg in ba.generated().items():
            with self.subTest(name):
                self.assertFalse([c for c in old if c.lower() in svg.lower()])

    def test_match_the_committed_files(self):
        for name, svg in ba.generated().items():
            with self.subTest(name):
                self.assertEqual((ba.OUTPUT / name).read_text(encoding="utf-8"), svg)


class FindMe(unittest.TestCase):
    """The Find me section is a row of icon-only links: the design system's link icons, named by their alt."""

    def anchors(self) -> list[str]:
        return re.findall(r"<a [^>]*>.*?</a>", FIND_ME)

    def test_is_one_icon_only_link_per_destination_in_order(self):
        anchors = self.anchors()
        self.assertEqual(len(anchors), len(FIND_ME_LINKS))
        for anchor, (href, stem, name) in zip(anchors, FIND_ME_LINKS):
            with self.subTest(name):
                self.assertEqual(
                    anchor,
                    f'<a href="{href}"><picture><source media="(prefers-color-scheme: dark)" '
                    f'srcset="assets/design-system/{stem}-dark.svg"><img src="assets/design-system/{stem}.svg" '
                    f'height="44" alt="{name}"></picture></a>',
                )

    def test_shows_no_words_and_no_tooltip(self):
        self.assertEqual(re.sub(r"<[^>]+>|\s+", "", FIND_ME[len("### Find me"):]), "")  # only the icons, no visible text
        self.assertNotRegex(FIND_ME, r"\btitle\s*=")

    def test_every_design_system_copy_is_shown(self):
        referenced = set(re.findall(r'(?:src|srcset)="assets/design-system/([^"]+\.svg)"', README))
        self.assertEqual({p.name for p in DESIGN_SYSTEM.iterdir()}, referenced)

    def test_icons_are_the_design_system_link_icons(self):
        for _, stem, name in FIND_ME_LINKS:
            for suffix in ("", "-dark"):
                with self.subTest(f"{stem}{suffix}"):
                    root = ET.parse(DESIGN_SYSTEM / f"{stem}{suffix}.svg").getroot()
                    self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")), ("46", "46", "0 0 46 46"))
                    title = root.find(f"{SVG}title")
                    assert title is not None
                    self.assertEqual(title.text, name)
                    self.assertEqual(title.get("id"), f"{stem}{suffix}-title")  # the spec id, one per file


if __name__ == "__main__":
    unittest.main()
