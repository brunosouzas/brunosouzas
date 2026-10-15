#!/usr/bin/env python3
"""Refresh the "Latest articles" list in README.md from the site's RSS feed.

The list lives between the markers <!-- articles:start --> and
<!-- articles:end -->. The script only rewrites that block, and leaves the
file untouched when nothing changed, so the scheduled workflow commits only
when a new article is out.

Usage: python3 scripts/update_articles.py [--feed URL] [--readme PATH] [--limit N]
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://brunosouzas.com/rss.xml"
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- articles:start -->"
END = "<!-- articles:end -->"
LIMIT = 5
TIMEOUT_S = 20
# The workflow commits what the feed says straight to main: accept only links to the site.
SITE = "https://brunosouzas.com/"
UNSAFE_IN_LINK = set(" \t\n()<>")
# GitHub turns these into links even inside link text, so a title must not carry them.
AUTOLINK_MARKERS = ("://", "www.", "@")


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    date: str  # as the site shows it: "15 Oct, 2026"


def parse_feed(xml_text: str, limit: int = LIMIT) -> list[Article]:
    """The newest `limit` items of an RSS 2.0 feed, in feed order."""
    channel = ET.fromstring(xml_text).find("channel")
    if channel is None:
        raise ValueError("not an RSS 2.0 feed: no <channel>")
    articles = []
    for item in channel.findall("item")[:limit]:
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if not title or not link:
            raise ValueError("feed item without a title or a link")
        if not link.startswith(SITE) or UNSAFE_IN_LINK & set(link):
            raise ValueError(f"feed link outside {SITE} or not safe in Markdown: {link!r}")
        if any(marker in title.lower() for marker in AUTOLINK_MARKERS):
            raise ValueError(f"feed title would render as a link: {title!r}")
        if not pub_date:
            raise ValueError(f"feed item without a pubDate: {title!r}")
        published = parsedate_to_datetime(pub_date)
        date = f"{published.day} {published:%b}, {published.year}"
        articles.append(Article(title, link, date))
    if not articles:
        raise ValueError("the feed has no items")
    return articles


def markdown_text(text: str) -> str:
    """Escape the characters that would break a Markdown link text, format it or open an HTML tag."""
    for char in "\\[]<>*_`":
        text = text.replace(char, f"\\{char}")
    return text


def render(articles: list[Article]) -> str:
    return "\n".join(f"- [{markdown_text(a.title)}]({a.link}) · {a.date}" for a in articles)


def replace_block(readme: str, block: str) -> str:
    """Put `block` between the markers, keeping everything else as it is."""
    start = readme.find(START)
    end = readme.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"README needs {START} followed by {END}")
    return f"{readme[: start + len(START)]}\n{block}\n{readme[end:]}"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "brunosouzas-profile-readme"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return response.read().decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the latest articles in README.md.")
    parser.add_argument("--feed", default=FEED_URL)
    parser.add_argument("--readme", type=Path, default=README)
    parser.add_argument("--limit", type=int, default=LIMIT)
    args = parser.parse_args(argv)

    current = args.readme.read_text(encoding="utf-8")
    updated = replace_block(current, render(parse_feed(fetch(args.feed), args.limit)))
    if updated == current:
        print("Latest articles already up to date.")
        return 0
    args.readme.write_text(updated, encoding="utf-8")
    print(f"Updated the latest articles in {args.readme.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
