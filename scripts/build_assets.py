#!/usr/bin/env python3
"""Build the profile README images from the site's own artwork.

The sources in assets/site/ are copies of public/images/home/ in the
brunosouzas.com repository, so the profile carries the same identity as the
site (the v2 identity of the design system @brunosouzas/design-system). This
script draws:

- assets/header.svg: the site's home banner, unchanged. The site shows one of
  two banners by the day (tracks on an even UTC day, route on an odd one, tracks
  without JavaScript); a README image cannot pick, so the header is the tracks
  banner, the one the site shows by default. The banner has no words, so the
  header has none: the README's alt text carries the name.
- assets/link-<slug>.svg and -dark.svg: the buttons (All articles, site,
  LinkedIn, email), in the site's button shapes and the design system's colours.

The words on the buttons are outlines (paths) drawn by scripts/glyphs.py from
fonts/SourceSans3-Bold.ttf, a copy of the design system's face: an SVG shown
through <img> cannot load a web font, and the files drawn here carry no CSS.

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
    card: str  # brand.<theme>.cardBg
    border: str  # the outline the site's icon tiles use: brand.light.text, brand.dark.borderStrong
    text: str  # brand.<theme>.text
    primary: str  # site.<theme>.primary, the site's primary button (.btn-primary)
    on_primary: str  # its text: white on light, brand.dark.bg on dark (the site's text-dark)
    accent: str  # brand.<theme>.accent


LIGHT = Theme(card="#FFFFFF", border="#121212", text="#121212", primary="#121212", on_primary="#FFFFFF", accent="#E04E17")
DARK = Theme(card="#1D1C1A", border="#ADA79D", text="#F1EEE8", primary="#F1EEE8", on_primary="#121110", accent="#FF7A45")
THEMES = (("", LIGHT), ("-dark", DARK))

FONT_FACE_STYLE = re.compile(r"\s*(?:@font-face\s*\{[^{}]*\}\s*)+")
STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL)
FORBIDDEN = {
    "an external or internal link": re.compile(r"\bhref="),
    "a <style> block other than embedded @font-face fonts": re.compile(r"<style\b"),
    "an external url()": re.compile(r"url\(\s*['\"]?(?!#)"),
    "a <script>": re.compile(r"<script\b"),
    "an embedded image or object": re.compile(r"<image\b|<foreignObject\b"),
    "currentColor": re.compile(r"currentColor"),
    "a blur or gradient": re.compile(r"\bfilter=|<filter\b|Gradient"),
    "inline CSS": re.compile(r'\bstyle="|\bclass="'),
}


def embedded_fonts(css: str) -> bool:
    """True when a <style> holds only @font-face rules whose every url() is an embedded font."""
    if not FONT_FACE_STYLE.fullmatch(css) or "@import" in css:
        return False
    urls = re.findall(r"url\(\s*['\"]?([^'\")\s]*)", css)
    return bool(urls) and all(u.startswith("data:font/") for u in urls)


def problems(svg: str) -> list[str]:
    """Why an SVG would not render as-is through <img> on GitHub; empty when it is fine."""
    rest = STYLE_BLOCK.sub(lambda m: "" if embedded_fonts(m.group(1)) else m.group(0), svg)
    return [what for what, pattern in FORBIDDEN.items() if pattern.search(rest)]


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


def nested(root: ET.Element, x: float, y: float, width: float, height: float | None = None, view: str = "") -> str:
    """Place a whole source SVG as a nested, scaled <svg>."""
    return (
        f'<svg x="{x:g}" y="{y:g}" width="{width:g}" height="{height or width:g}" '
        f'viewBox="{view or root.get("viewBox")}">{inner(root)}</svg>'
    )


def document(width: float, height: float, prefix: str, title: str, desc: str, body: str) -> str:
    return (
        f'<svg xmlns="{SVG_NS}" width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}" '
        f'role="img" aria-labelledby="{prefix}-t {prefix}-d" font-family="{FONT}">\n'
        f'  <title id="{prefix}-t">{escape(title)}</title>\n'
        f'  <desc id="{prefix}-d">{escape(desc)}</desc>\n'
        f"{body}\n</svg>\n"
    )


# Header ---------------------------------------------------------------------

HEADER_SOURCE = "home-banner-tracks.svg"


def header() -> str:
    """The site's home banner as it is (1200x420, the design system's banner size), with its own description."""
    banner = load(HEADER_SOURCE)
    desc = next((e.text or "" for e in banner if tag(e) == "desc"), "").strip()
    width, height = (float(v) for v in banner.get("viewBox", "").split()[2:])
    return document(width, height, "hd", "Bruno Souza, brunosouzas.com", desc, f"  {inner(banner)}")


# Buttons ----------------------------------------------------------------------

LINK_H = 44  # drawn at the size the README shows it (height="44")
OUTLINE = 2
LABEL_SIZE = 17
ICON = 28  # the site's icon tile, without the room its 46-unit canvas keeps around it
ICON_X = 8
GAP = 10
PAD = 20  # the site's .btn is px-5
TILE_VIEW = "0.75 0.75 40.5 40.5"  # the icon's tile (38 units at 2,2) with its 2.5 outline
ARROW_W = 14


@dataclass(frozen=True)
class Link:
    slug: str
    label: str
    icon: str  # a source file stem, or "" for the primary button with an arrow


LINKS = [
    Link("articles", "All articles", ""),
    Link("site", "brunosouzas.com", "avatar"),
    Link("linkedin", "LinkedIn", "social-linkedin"),
    Link("email", "Email", "social-email"),
]

_font: glyphs.Font | None = None


def label(text: str) -> glyphs.Line:
    global _font
    if _font is None:
        _font = glyphs.Font(FONT_FILE)
    return _font.line(text)


def baseline() -> float:
    """The label's baseline, centring Source Sans 3's cap height (660/1000) in the button."""
    return round(LINK_H / 2 + 0.66 * LABEL_SIZE / 2, 2)


def icon(item: Link, dark: bool) -> str:
    y = (LINK_H - ICON) / 2
    if item.icon == "avatar":  # the brand symbol on its square tile, rounded like the social tiles
        return (
            f'<defs><clipPath id="lk-a"><rect x="{ICON_X}" y="{y:g}" width="{ICON}" height="{ICON}" rx="7"/></clipPath></defs>'
            f'<g clip-path="url(#lk-a)">{nested(load("avatar.svg"), ICON_X, y, ICON)}</g>'
        )
    name = f"{item.icon}{'-dark' if dark else ''}.svg"
    return nested(load(name), ICON_X, y, ICON, view=TILE_VIEW)


def arrow(x: float, theme: Theme) -> str:
    """A right arrow in the accent."""
    y = LINK_H / 2
    return (
        f'<path d="M{x:g},{y:g} H{x + ARROW_W:g} M{x + ARROW_W - 5:g},{y - 5:g} L{x + ARROW_W:g},{y:g} '
        f'L{x + ARROW_W - 5:g},{y + 5:g}" fill="none" stroke="{theme.accent}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def link(item: Link, theme: Theme, dark: bool) -> str:
    words = label(item.label)
    text_w = words.width(LABEL_SIZE)
    half = OUTLINE / 2
    if item.icon:  # outline button (the site's .btn-outline-primary), on the card colour
        text_x = ICON_X + ICON + GAP
        width = round(text_x + text_w + PAD)
        fill, stroke, ink = theme.card, theme.border, theme.text
        extra = icon(item, dark)
    else:  # primary button (the site's .btn-primary), with the accent arrow
        text_x = PAD
        width = round(text_x + text_w + GAP + ARROW_W + PAD)
        fill, stroke, ink = theme.primary, theme.primary, theme.on_primary
        extra = arrow(round(text_x + text_w + GAP, 2), theme)
    body = (
        f'  <rect x="{half:g}" y="{half:g}" width="{width - OUTLINE:g}" height="{LINK_H - OUTLINE:g}" '
        f'rx="{RADIUS_PILL - half:g}" fill="{fill}" stroke="{stroke}" stroke-width="{OUTLINE}"/>\n'
        f"  {extra}\n"
        f"  {words.svg(round(text_x, 2), baseline(), LABEL_SIZE, ink)}"
    )
    return document(width, LINK_H, "lk", item.label, f"Button: {item.label}.", body)


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
            files[f"link-{item.slug}{suffix}.svg"] = link(item, theme, suffix == "-dark")
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
