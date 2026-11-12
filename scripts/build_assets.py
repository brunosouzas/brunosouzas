#!/usr/bin/env python3
"""Build the profile README images from the site's own artwork.

The source in assets/site/ is a copy from the brunosouzas.com repository, so
the profile carries the same identity as the site (the v2 identity of the
design system @brunosouzas/design-system). This script draws:

- assets/header.svg: the site's share image (assets-src/og/og-en.svg in the
  brunosouzas.com repository, the source of its /og.image.png), unchanged: the
  slogan, the symbol, the four category badges and the signature. Its slogan is
  text in Source Serif 4, embedded in the image as the design system writes it
  (see below); the README's alt text carries the name and the slogan.
- assets/link-articles.svg and -dark.svg: the All articles button, in the
  site's primary button shape and the design system's colours.

The button's words are outlines (paths) drawn by scripts/glyphs.py from
fonts/SourceSans3-Bold.ttf, a copy of the design system's face: an SVG shown
through <img> cannot load a web font, and the files drawn here carry no CSS.

The Find me icons are not drawn here: assets/design-system/ holds the design
system's link icons as its cover command writes them (see AGENTS.md).

It also holds the article thumbnail (the site's cover with rounded corners)
that scripts/update_articles.py draws for each of the latest articles.

GitHub shows README images through <img>, so every SVG is self-contained:
no external references, no scripts, fixed colours, and no CSS except the one
form the design system writes into the site's covers (its ADR 0008): a <style>
that holds only @font-face rules whose fonts are embedded as data: URLs.
`problems()` checks that rule, for these files and for the covers downloaded
from the site.

Usage: python3 scripts/build_assets.py
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import glyphs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "site"
OUTPUT = ROOT / "assets"
FONT_FILE = ROOT / "fonts" / "SourceSans3-Bold.ttf"

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

# The design system's tokens (tokens/generated/tokens.json, 0.9.x), by token path.
FONT = "'Source Sans 3', 'Helvetica Neue', Helvetica, Arial, sans-serif"  # font.sans
RADIUS_PILL = 22  # radius.pill


@dataclass(frozen=True)
class Theme:
    primary: str  # site.<theme>.primary, the site's primary button (.btn-primary)
    on_primary: str  # its text: white on light, brand.dark.bg on dark (the site's text-dark)
    accent: str  # brand.<theme>.accent


LIGHT = Theme(primary="#121212", on_primary="#FFFFFF", accent="#E04E17")
DARK = Theme(primary="#F1EEE8", on_primary="#121110", accent="#FF7A45")
THEMES = (("", LIGHT), ("-dark", DARK))

FONT_FACE_BLOCK = re.compile(r"@font-face\s*\{([^{}]*)\}", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*['\"]?\s*([^'\")\s]*)", re.IGNORECASE)
NOT_FRAGMENT_URL = re.compile(r"url\(\s*['\"]?\s*(?![\s'\"#])", re.IGNORECASE)  # a url() that is not a #fragment
# Checked on the raw text too: a processing instruction (<?xml-stylesheet href=...?>) never reaches the tree.
RAW_FORBIDDEN = {
    "an external or internal link": re.compile(r"\bhref\s*=", re.IGNORECASE),
    "an external url()": re.compile(r"url\(\s*['\"]?\s*(?:https?:|//)", re.IGNORECASE),
    "currentColor": re.compile(r"currentColor", re.IGNORECASE),
}
PROBLEMS = (
    "not well-formed XML",
    "an external or internal link",
    "a <style> block other than embedded @font-face fonts",
    "a CSS escape",
    "an external url()",
    "a <script>",
    "an event handler",
    "an embedded image or object",
    "currentColor",
    "a blur or gradient",
    "inline CSS",
)


def embedded_fonts(css: str) -> bool:
    """True when a <style> holds only @font-face rules whose every url() is an embedded font.

    A backslash (a CSS escape such as `u\\72l(`) is refused outright: it could spell a url()
    or a property the patterns here do not see.
    """
    blocks = FONT_FACE_BLOCK.findall(css)
    if "\\" in css or not blocks or FONT_FACE_BLOCK.sub("", css).strip():
        return False
    for block in blocks:
        urls = CSS_URL.findall(block)
        if len(urls) != len(re.findall(r"url\(", block, re.IGNORECASE)):
            return False
        if not urls or not all(u.lower().startswith("data:font/") for u in urls):
            return False
    return True


def local_name(name: str) -> str:
    """An element or attribute name without its namespace ({uri}name) or prefix (p:name)."""
    return name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def problems(svg: str) -> list[str]:
    """Why an SVG would not render as-is through <img> on GitHub; empty when it is fine.

    The checks run on the parsed tree, so a namespace prefix (<s:script>), spacing
    (href =) or quoting (style='...') does not hide a construct; a few also run on
    the raw text, which holds what the tree drops.
    """
    found = {what for what, pattern in RAW_FORBIDDEN.items() if pattern.search(svg)}
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return ["not well-formed XML"]
    for element in root.iter():
        name = local_name(element.tag).lower() if isinstance(element.tag, str) else ""
        if name == "style":
            css = "".join(element.itertext())
            if "\\" in css:
                found.add("a CSS escape")
            if not embedded_fonts(css):
                found.add("a <style> block other than embedded @font-face fonts")
        elif name == "script":
            found.add("a <script>")
        elif name in ("image", "foreignobject"):
            found.add("an embedded image or object")
        elif name == "filter" or name.endswith("gradient"):
            found.add("a blur or gradient")
        for attribute, value in element.attrib.items():
            key = local_name(attribute).lower()
            if key == "href":
                found.add("an external or internal link")
            elif key.startswith("on"):
                found.add("an event handler")
            elif key in ("style", "class"):
                found.add("inline CSS")
            elif key == "filter":
                found.add("a blur or gradient")
            if "\\" in value:
                found.add("a CSS escape")
            if NOT_FRAGMENT_URL.search(value):
                found.add("an external url()")
            if "currentcolor" in value.lower():
                found.add("currentColor")
    return [what for what in PROBLEMS if what in found]


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def load(name: str) -> ET.Element:
    return ET.parse(SOURCE / name).getroot()


def drop_ns(markup: str) -> str:
    """ElementTree writes the default namespace on each fragment; the outer svg already declares it."""
    return markup.replace(f' xmlns="{SVG_NS}"', "")


def inner(root: ET.Element) -> str:
    """The drawing of a source SVG without its title and desc."""
    kept = [child for child in root if tag(child) not in ("title", "desc")]
    return drop_ns("".join(ET.tostring(e, encoding="unicode") for e in kept))


def nested(root: ET.Element, x: float, y: float, width: float, height: float | None = None) -> str:
    """Place a whole source SVG as a nested, scaled <svg>."""
    return (
        f'<svg x="{x:g}" y="{y:g}" width="{width:g}" height="{height or width:g}" '
        f'viewBox="{root.get("viewBox")}">{inner(root)}</svg>'
    )


def document(
    width: float, height: float, prefix: str, title: str, desc: str, body: str, font_family: str | None = FONT
) -> str:
    """A whole SVG file; `font_family=None` for a drawing with no <text> to inherit it."""
    family = f' font-family="{font_family}"' if font_family else ""
    return (
        f'<svg xmlns="{SVG_NS}" width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}" '
        f'role="img" aria-labelledby="{prefix}-t {prefix}-d"{family}>\n'
        f'  <title id="{prefix}-t">{escape(title)}</title>\n'
        f'  <desc id="{prefix}-d">{escape(desc)}</desc>\n'
        f"{body}\n</svg>\n"
    )


# Header ---------------------------------------------------------------------

HEADER_SOURCE = "og-en.svg"


def header() -> str:
    """The site's share image as it is (1200x630, the Open Graph size), with its own description."""
    image = load(HEADER_SOURCE)
    desc = next((e.text or "" for e in image if tag(e) == "desc"), "").strip()
    width, height = (float(v) for v in image.get("viewBox", "").split()[2:])
    return document(width, height, "hd", "Bruno Souza, brunosouzas.com", desc, f"  {inner(image)}")


# Button -----------------------------------------------------------------------

LINK_H = 44  # drawn at the size the README shows it (height="44")
OUTLINE = 2
LABEL_SIZE = 17
GAP = 10
PAD = 20  # the site's .btn is px-5
ARROW_W = 14


@dataclass(frozen=True)
class Link:
    slug: str
    label: str


LINKS = [Link("articles", "All articles")]

_font: glyphs.Font | None = None


def label(text: str) -> glyphs.Line:
    global _font
    if _font is None:
        _font = glyphs.Font(FONT_FILE)
    return _font.line(text)


def baseline() -> float:
    """The label's baseline, centring Source Sans 3's cap height (660/1000) in the button."""
    return round(LINK_H / 2 + 0.66 * LABEL_SIZE / 2, 2)


def arrow(x: float, theme: Theme) -> str:
    """A right arrow in the accent."""
    y = LINK_H / 2
    return (
        f'<path d="M{x:g},{y:g} H{x + ARROW_W:g} M{x + ARROW_W - 5:g},{y - 5:g} L{x + ARROW_W:g},{y:g} '
        f'L{x + ARROW_W - 5:g},{y + 5:g}" fill="none" stroke="{theme.accent}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def link(item: Link, theme: Theme) -> str:
    """The primary button (the site's .btn-primary), with the accent arrow."""
    words = label(item.label)
    text_w = words.width(LABEL_SIZE)
    half = OUTLINE / 2
    text_x = PAD
    width = round(text_x + text_w + GAP + ARROW_W + PAD)
    fill, ink = theme.primary, theme.on_primary  # the primary button is outlined in its own fill colour
    extra = arrow(round(text_x + text_w + GAP, 2), theme)
    body = (
        f'  <rect x="{half:g}" y="{half:g}" width="{width - OUTLINE:g}" height="{LINK_H - OUTLINE:g}" '
        f'rx="{RADIUS_PILL - half:g}" fill="{fill}" stroke="{fill}" stroke-width="{OUTLINE}"/>\n'
        f"  {extra}\n"
        f"  {words.svg(round(text_x, 2), baseline(), LABEL_SIZE, ink)}"
    )
    return document(width, LINK_H, "lk", item.label, f"Button: {item.label}.", body, font_family=None)  # words are paths


# Article thumbnail ----------------------------------------------------------------

COVER_W, COVER_H = 800, 420  # the site's cover canvas
THUMB_RADIUS = 24  # the site's rounded cover corners, at cover scale


def thumbnail(cover_svg: str, title: str) -> str:
    """The article's cover with rounded corners, as the site lists it next to the title."""
    cover = ET.fromstring(cover_svg)
    cover_desc = next((e.text or "" for e in cover if tag(e) == "desc"), "").strip()
    body = (
        f'  <defs><clipPath id="pfa-c"><rect width="{COVER_W}" height="{COVER_H}" rx="{THUMB_RADIUS}"/>'
        f"</clipPath></defs>\n"
        f'  <g clip-path="url(#pfa-c)">{nested(cover, 0, 0, COVER_W, COVER_H)}</g>'
    )
    return document(COVER_W, COVER_H, "pfa", f"Cover: {title}", cover_desc or f"Cover of {title}.", body)


# Files --------------------------------------------------------------------------


def generated() -> dict[str, str]:
    """Every file this script owns in assets/, by name."""
    files = {"header.svg": header()}
    for suffix, theme in THEMES:
        for item in LINKS:
            files[f"link-{item.slug}{suffix}.svg"] = link(item, theme)
    return files


def main() -> None:
    files = generated()
    for name, content in files.items():
        (OUTPUT / name).write_text(content, encoding="utf-8")
        print(f"wrote assets/{name}")
    # The top level of assets/ belongs to this script: drop what it no longer draws.
    for old in sorted(OUTPUT.glob("*.svg")):
        if old.name not in files:
            old.unlink()
            print(f"removed assets/{old.name}")


if __name__ == "__main__":
    main()
