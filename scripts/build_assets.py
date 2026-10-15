#!/usr/bin/env python3
"""Build the profile README images from the site's own artwork.

The sources in assets/site/ are copies of public/images/home/ in the
brunosouzas.com repository, so the profile carries the same brand as the
site. This script draws:

- assets/header.svg: the site's home banner with the avatar, the name and
  the site address on top.
- assets/link-<slug>.svg and -dark.svg: the buttons (All articles, site,
  LinkedIn, email).

It also holds the article thumbnail (the site's cover with rounded corners)
that scripts/update_articles.py draws for each of the latest articles.

GitHub shows README images through <img>, so every SVG is self-contained:
no external references, no CSS, no scripts, fixed colours only.
`problems()` checks that rule, for these files and for the covers downloaded
from the site.

Usage: python3 scripts/build_assets.py
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "site"
OUTPUT = ROOT / "assets"

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

FONT = "Lato, 'Helvetica Neue', Helvetica, Arial, sans-serif"

# The site's palette (designer skill, card illustrations).
INK = "#0A1033"
NAVY = "#14215A"
RING = "#1C2D74"
WHITE = "#FFFFFF"
LIGHT_BLUE = "#8FB2FF"
YELLOW = "#FFD25A"
GREEN = "#3DDC84"
# The site's dark-theme accents (category-*-dark.svg, social-*-dark.svg).
DARK_SHADOW = "#4C5CB8"
DARK_HALO = "#EEF1FF"

FORBIDDEN = {
    "an external or internal link": re.compile(r"\bhref="),
    "a <style> block": re.compile(r"<style\b"),
    "a <script>": re.compile(r"<script\b"),
    "an embedded image or object": re.compile(r"<image\b|<foreignObject\b"),
    "currentColor": re.compile(r"currentColor"),
    "a blur or gradient": re.compile(r"\bfilter=|<filter\b|Gradient"),
    "inline CSS": re.compile(r'\bstyle="|\bclass="'),
}


def problems(svg: str) -> list[str]:
    """Why an SVG would not render as-is through <img> on GitHub; empty when it is fine."""
    return [what for what, pattern in FORBIDDEN.items() if pattern.search(svg)]


@dataclass(frozen=True)
class Theme:
    card: str
    outline: str
    shadow: str
    text: str


LIGHT = Theme(card=WHITE, outline=INK, shadow=INK, text=INK)
DARK = Theme(card=NAVY, outline=DARK_SHADOW, shadow=DARK_SHADOW, text=WHITE)
THEMES = (("", LIGHT), ("-dark", DARK))


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def load(name: str) -> ET.Element:
    return ET.parse(SOURCE / name).getroot()


def drop_ns(markup: str) -> str:
    """ElementTree writes the default namespace on each fragment; the outer svg already declares it."""
    return markup.replace(f' xmlns="{SVG_NS}"', "")


def inner(root: ET.Element, skip_background: bool = False) -> str:
    """The drawing of a source SVG without its title and desc.

    With skip_background, also drop the background rect, the defs and the
    clipped ring group, so the drawing can sit on another background.
    """
    kept = []
    for child in root:
        name = tag(child)
        if name in ("title", "desc"):
            continue
        if skip_background and (
            name == "defs"
            or (name == "rect" and child.get("width") == root.get("width"))
            or child.get("clip-path")
        ):
            continue
        kept.append(child)
    return drop_ns("".join(ET.tostring(e, encoding="unicode") for e in kept))


def nested(root: ET.Element, x: float, y: float, width: float, height: float | None = None) -> str:
    """Place a whole source SVG as a nested, scaled <svg>."""
    return (
        f'<svg x="{x}" y="{y}" width="{width}" height="{height or width}" '
        f'viewBox="{root.get("viewBox")}">{inner(root)}</svg>'
    )


def rings(cx: float, cy: float, start: int, stop: int, clip: str) -> str:
    circles = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>' for r in range(start, stop, 28))
    return f'<g clip-path="url(#{clip})" fill="none" stroke="{RING}" stroke-width="2">{circles}</g>'


def document(width: int, height: int, prefix: str, title: str, desc: str, body: str) -> str:
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="{prefix}-t {prefix}-d" font-family="{FONT}">\n'
        f'  <title id="{prefix}-t">{escape(title)}</title>\n'
        f'  <desc id="{prefix}-d">{escape(desc)}</desc>\n'
        f"{body}\n</svg>\n"
    )


def card(width: int, height: int, theme: Theme, offset: int = 6, radius: int = 18) -> str:
    """A flat card with an outline and a hard offset shadow, the site's style."""
    w, h = width - offset - 4, height - offset - 4
    return (
        f'  <rect x="{2 + offset}" y="{2 + offset}" width="{w}" height="{h}" rx="{radius}" fill="{theme.shadow}"/>\n'
        f'  <rect x="2" y="2" width="{w}" height="{h}" rx="{radius}" fill="{theme.card}" '
        f'stroke="{theme.outline}" stroke-width="3"/>\n'
    )


# Header ---------------------------------------------------------------------

HEADER_W, HEADER_H = 1200, 580
BANNER_DROP = 160  # the banner sits lower, leaving a quiet band for the name


def header() -> str:
    banner = load("home-banner.svg")
    avatar = load("avatar.svg")
    av_x, av_y, av = 60, 40, 112
    pill_x, pill_y, pill_w, pill_h = 896, 66, 244, 50
    body = f"""  <defs><clipPath id="hd-f"><rect width="{HEADER_W}" height="{HEADER_H}" rx="20"/></clipPath></defs>
  <rect width="{HEADER_W}" height="{HEADER_H}" rx="20" fill="{NAVY}"/>
  {rings(600, 225 + BANNER_DROP, 60, 760, "hd-f")}
  <g transform="translate(0 {BANNER_DROP})">{inner(banner, skip_background=True)}</g>
  <rect x="{av_x + 8}" y="{av_y + 8}" width="{av}" height="{av}" rx="12" fill="{INK}"/>
  {nested(avatar, av_x, av_y, av)}
  <rect x="{av_x}" y="{av_y}" width="{av}" height="{av}" rx="10" fill="none" stroke="{INK}" stroke-width="4"/>
  <rect x="{pill_x + 6}" y="{pill_y + 6}" width="{pill_w}" height="{pill_h}" rx="{pill_h / 2}" fill="{INK}"/>
  <rect x="{pill_x}" y="{pill_y}" width="{pill_w}" height="{pill_h}" rx="{pill_h / 2}" fill="{YELLOW}" stroke="{INK}" stroke-width="4"/>
  <text x="{av_x + av + 32}" y="{av_y + 60}" font-size="54" font-weight="800" fill="{WHITE}">Bruno Souza</text>
  <text x="{av_x + av + 34}" y="{av_y + 100}" font-size="24" font-weight="700" fill="{LIGHT_BLUE}">Integration · MuleSoft · AI-assisted engineering</text>
  <text x="{pill_x + pill_w / 2}" y="{pill_y + 33}" font-size="22" font-weight="800" fill="{INK}" text-anchor="middle">brunosouzas.com</text>"""
    return document(
        HEADER_W,
        HEADER_H,
        "hd",
        "Bruno Souza: integration, MuleSoft and AI-assisted engineering",
        "Header of the GitHub profile, drawn from the brunosouzas.com home banner. "
        "Top left, the illustrated avatar (a bearded engineer in a cap with a small AI robot), "
        "the name Bruno Souza and the line Integration, MuleSoft, AI-assisted engineering; "
        "top right, a yellow pill with the address brunosouzas.com. Below, a web application "
        "and a server stack send requests through pipes into an orange integration hub fed by "
        "a green AI robot; the result passes three CI/CD checks into a cloud, and an open "
        "notebook stands for the articles.",
        body,
    )


# Buttons ----------------------------------------------------------------------

LINK_H = 64
ICON = 40


@dataclass(frozen=True)
class Link:
    slug: str
    label: str
    width: int
    icon: str  # a source file stem, "avatar", or "arrow" (drawn here)


LINKS = [
    Link("articles", "All articles", 190, "arrow"),
    Link("site", "brunosouzas.com", 250, "avatar"),
    Link("linkedin", "LinkedIn", 170, "social-linkedin"),
    Link("email", "Email", 150, "social-email"),
]


def arrow_icon(x: float, y: float, dark: bool) -> str:
    """A green tile with an arrow, drawn like the site's social icons (46x46 at this scale)."""
    s = (ICON + 4) / 46
    if dark:
        under = (
            f'<rect x="4" y="4" width="41" height="41" rx="11" fill="{DARK_SHADOW}"/>'
            f'<rect x="0.5" y="0.5" width="41" height="41" rx="11" fill="{DARK_HALO}"/>'
        )
    else:
        under = f'<rect x="5" y="5" width="38" height="38" rx="9" fill="{INK}"/>'
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f})">{under}'
        f'<rect x="2" y="2" width="38" height="38" rx="9" fill="{GREEN}" stroke="{INK}" stroke-width="2.5"/>'
        f'<path d="M11,21 H30 M23,14 L30,21 L23,28" fill="none" stroke="{INK}" stroke-width="3.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/></g>'
    )


def link(item: Link, theme: Theme, dark: bool) -> str:
    if item.icon == "avatar":
        icon = nested(load("avatar.svg"), 12, 9, ICON)
    elif item.icon == "arrow":
        icon = arrow_icon(12, 9, dark)
    else:
        icon = nested(load(f"{item.icon}{'-dark' if dark else ''}.svg"), 12, 9, ICON + 4)
    body = (
        card(item.width, LINK_H, theme, offset=5, radius=14)
        + f"  {icon}\n"
        + f'  <text x="{12 + ICON + 12}" y="{LINK_H / 2 + 4}" font-size="19" font-weight="800" '
        f'fill="{theme.text}">{escape(item.label)}</text>'
    )
    return document(item.width, LINK_H, "lk", item.label, f"Button: {item.label}.", body)


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
