#!/usr/bin/env python3
"""Build the profile README images from the site's own artwork.

The sources in assets/site/ are copies of public/images/home/ in the
brunosouzas.com repository, so the profile carries the same brand as the
site. This script composes them into the images the README shows:

- assets/header.svg: the site's home banner as the background, with the
  avatar, the name and the site address on top.
- assets/topic-<slug>.svg and -dark.svg: one card per site category.
- assets/link-<slug>.svg and -dark.svg: the link buttons (site, LinkedIn, email).

GitHub shows README images through <img>, so every SVG is self-contained:
no external references, no CSS, no scripts, fixed colours only.

Usage: python3 scripts/build_assets.py
"""

from __future__ import annotations

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
# The site's dark-theme accents (category-*-dark.svg, social-*-dark.svg).
DARK_SHADOW = "#4C5CB8"


@dataclass(frozen=True)
class Theme:
    card: str
    outline: str
    shadow: str
    text: str


LIGHT = Theme(card=WHITE, outline=INK, shadow=INK, text=INK)
DARK = Theme(card=NAVY, outline=DARK_SHADOW, shadow=DARK_SHADOW, text=WHITE)


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def load(name: str) -> ET.Element:
    return ET.parse(SOURCE / name).getroot()


def serialise(elements: list[ET.Element]) -> str:
    return "".join(ET.tostring(e, encoding="unicode") for e in elements)


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
    return drop_ns(serialise(kept))


def nested(root: ET.Element, x: float, y: float, size: float) -> str:
    """Place a whole source SVG as a nested, scaled <svg>."""
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
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


# Topic cards ------------------------------------------------------------------

TOPIC_W, TOPIC_H = 220, 200


@dataclass(frozen=True)
class Topic:
    slug: str
    label: str


TOPICS = [
    Topic("integration", "Integration"),
    Topic("delivery", "Delivery"),
    Topic("ai-engineering", "AI engineering"),
    Topic("personal-tools", "Personal tools"),
]


def card(width: int, height: int, theme: Theme, offset: int = 6, radius: int = 18) -> str:
    w, h = width - offset - 4, height - offset - 4
    return (
        f'  <rect x="{2 + offset}" y="{2 + offset}" width="{w}" height="{h}" rx="{radius}" fill="{theme.shadow}"/>\n'
        f'  <rect x="2" y="2" width="{w}" height="{h}" rx="{radius}" fill="{theme.card}" '
        f'stroke="{theme.outline}" stroke-width="3"/>\n'
    )


def topic(item: Topic, theme: Theme, dark: bool) -> str:
    icon = load(f"category-{item.slug}{'-dark' if dark else ''}.svg")
    icon_desc = next(e.text for e in icon if tag(e) == "desc")
    size = 112
    x = (TOPIC_W - 6 - size) / 2 + 4
    body = (
        card(TOPIC_W, TOPIC_H, theme)
        + "  "
        + nested(icon, x, 18, size)
        + f'\n  <text x="{(TOPIC_W - 6) / 2}" y="164" font-size="21" font-weight="800" '
        f'fill="{theme.text}" text-anchor="middle">{escape(item.label)}</text>'
    )
    return document(TOPIC_W, TOPIC_H, "tp", item.label, f"Category card. {icon_desc}", body)


# Link buttons -------------------------------------------------------------------

LINK_H = 64


@dataclass(frozen=True)
class Link:
    slug: str
    label: str
    width: int
    icon: str  # source file stem; "avatar" uses the avatar


LINKS = [
    Link("site", "brunosouzas.com", 250, "avatar"),
    Link("linkedin", "LinkedIn", 170, "social-linkedin"),
    Link("email", "Email", 150, "social-email"),
]


def link(item: Link, theme: Theme, dark: bool) -> str:
    size = 40
    if item.icon == "avatar":
        icon = nested(load("avatar.svg"), 12, 9, size)
    else:
        icon = nested(load(f"{item.icon}{'-dark' if dark else ''}.svg"), 12, 9, size + 4)
    body = (
        card(item.width, LINK_H, theme, offset=5, radius=14)
        + f"  {icon}\n"
        + f'  <text x="{12 + size + 12}" y="{LINK_H / 2 + 4}" font-size="19" font-weight="800" '
        f'fill="{theme.text}">{escape(item.label)}</text>'
    )
    return document(item.width, LINK_H, "lk", item.label, f"Link button: {item.label}.", body)


def main() -> None:
    files = {"header.svg": header()}
    for dark, theme in ((False, LIGHT), (True, DARK)):
        suffix = "-dark" if dark else ""
        for item in TOPICS:
            files[f"topic-{item.slug}{suffix}.svg"] = topic(item, theme, dark)
        for item in LINKS:
            files[f"link-{item.slug}{suffix}.svg"] = link(item, theme, dark)
    for name, content in files.items():
        (OUTPUT / name).write_text(content, encoding="utf-8")
        print(f"wrote assets/{name}")


if __name__ == "__main__":
    main()
