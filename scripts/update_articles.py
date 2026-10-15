#!/usr/bin/env python3
"""Refresh the latest articles in README.md from the site's RSS feed.

For each of the newest articles, the script downloads its cover (the feed's
media:content), saves it as a rounded thumbnail in assets/articles/, and
rewrites the README block between <!-- articles:start --> and
<!-- articles:end -->: one row per article, the thumbnail on the left and the
title, date and description on the right, as the site lists its articles.

It writes only what changed and removes the thumbnails of articles that left the
list, so the scheduled workflow commits only when a new article is out.

Usage: python3 scripts/update_articles.py [--feed URL] [--limit N]
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_assets as ba  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
THUMBS = ROOT / "assets" / "articles"
FEED_URL = "https://brunosouzas.com/rss.xml"
START = "<!-- articles:start -->"
END = "<!-- articles:end -->"
LIMIT = 4
THUMB_WIDTH = 200
TIMEOUT_S = 20
MEDIA = "{http://search.yahoo.com/mrss/}content"
# The workflow commits what the feed says straight to main: accept only the site's own addresses.
SITE = "https://brunosouzas.com/"
UNSAFE_IN_URL = set(" \t\n\"'()<>")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# The parser expands DTD entities, which could hide markup from the checks on the raw text.
DTD = re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE)


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    date: str  # as the site shows it: "15 Oct, 2026"
    cover: str
    description: str = ""

    @property
    def slug(self) -> str:
        return self.link.rstrip("/").rsplit("/", 1)[-1]


def site_url(url: str, what: str) -> str:
    if not url.startswith(SITE) or UNSAFE_IN_URL & set(url):
        raise ValueError(f"feed {what} outside {SITE} or not safe in HTML: {url!r}")
    return url


def parse_feed(xml_text: str, limit: int = LIMIT) -> list[Article]:
    """The newest `limit` items of an RSS 2.0 feed, in feed order."""
    channel = ET.fromstring(xml_text).find("channel")
    if channel is None:
        raise ValueError("not an RSS 2.0 feed: no <channel>")
    articles = []
    for item in channel.findall("item")[:limit]:
        title = " ".join((item.findtext("title") or "").split())
        description = " ".join((item.findtext("description") or "").split())
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        media = item.find(MEDIA)
        cover = (media.get("url") or "").strip() if media is not None else ""
        if not title or not link:
            raise ValueError("feed item without a title or a link")
        if not pub_date:
            raise ValueError(f"feed item without a pubDate: {title!r}")
        if not cover:
            raise ValueError(f"feed item without a cover (media:content): {title!r}")
        published = parsedate_to_datetime(pub_date)
        article = Article(
            title,
            site_url(link, "link"),
            f"{published.day} {published:%b}, {published.year}",
            site_url(cover, "cover"),
            description,
        )
        if not SLUG.match(article.slug):
            raise ValueError(f"feed link does not end in a slug: {link!r}")
        articles.append(article)
    if not articles:
        raise ValueError("the feed has no items")
    return articles


def thumbnail_file(article: Article, cover_svg: str) -> tuple[str, str]:
    """The thumbnail of one article: its file name and content."""
    if DTD.search(cover_svg):
        raise ValueError(f"cover of {article.slug} has a DTD, which is not allowed")
    issues = ba.problems(cover_svg)
    if issues:
        raise ValueError(f"cover of {article.slug} would not render on GitHub: {', '.join(issues)}")
    svg = ba.thumbnail(cover_svg, article.title)
    issues = ba.problems(svg)  # check what is written, not only what was read
    if issues:
        raise ValueError(f"thumbnail of {article.slug} would not render on GitHub: {', '.join(issues)}")
    return f"{article.slug}.svg", svg


def render(articles: list[Article]) -> str:
    """The README block: one row per article, as raw HTML so GitHub does not reformat the feed text.

    Each row floats the linked thumbnail left of the linked title, the date and the
    description; a rule separates the rows, as on the site's article lists.
    """
    rows = []
    for a in articles:
        description = f"<br>{escape(a.description)}" if a.description else ""
        rows.append(
            f'<p><a href="{a.link}"><img align="left" width="{THUMB_WIDTH}" '
            f'src="assets/articles/{a.slug}.svg" alt="Cover: {escape(a.title)}"></a>'
            f'<a href="{a.link}"><b>{escape(a.title)}</b></a><br>'
            f'<sub>{a.date}</sub>{description}<br clear="left"></p>'
        )
    return "\n<hr>\n".join(rows)


def replace_block(readme: str, block: str) -> str:
    """Put `block` between the markers, keeping everything else as it is."""
    start = readme.find(START)
    end = readme.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"README needs {START} followed by {END}")
    return f"{readme[: start + len(START)]}\n{block}\n{readme[end:]}"


def check_final_url(requested: str, final: str) -> None:
    """A request to the site must not be redirected away from it."""
    if requested.startswith(SITE) and not final.startswith(SITE):
        raise ValueError(f"{requested} redirected outside {SITE}: {final}")


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "brunosouzas-profile-readme"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        check_final_url(url, response.geturl())
        return response.read().decode("utf-8")


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def update(
    feed_text: str,
    readme: Path,
    thumbs_dir: Path,
    limit: int = LIMIT,
    get: Callable[[str], str] = fetch,
) -> list[str]:
    """Bring the thumbnails and the README block in step with the feed; return what changed."""
    articles = parse_feed(feed_text, limit)
    # Build everything before writing anything, so a bad item leaves the repository untouched.
    files = dict(thumbnail_file(article, get(article.cover)) for article in articles)
    updated = replace_block(readme.read_text(encoding="utf-8"), render(articles))

    changed = []
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        if write_if_changed(thumbs_dir / name, content):
            changed.append(f"assets/articles/{name}")
    for stale in sorted(thumbs_dir.glob("*.svg")):
        if stale.name not in files:
            stale.unlink()
            changed.append(f"assets/articles/{stale.name} (removed)")
    if write_if_changed(readme, updated):
        changed.append(readme.name)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the latest articles in README.md.")
    parser.add_argument("--feed", default=FEED_URL)
    parser.add_argument("--limit", type=int, default=LIMIT)
    args = parser.parse_args(argv)

    changed = update(fetch(args.feed), README, THUMBS, args.limit)
    print("\n".join(f"updated {c}" for c in changed) or "Latest articles already up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
