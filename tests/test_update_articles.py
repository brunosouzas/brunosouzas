import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import update_articles as ua  # noqa: E402

COVER_URL = "https://brunosouzas.com/_astro/{}-card.abc123.svg"
COVER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="420" viewBox="0 0 800 420">'
    "<title>t</title><desc>A cover.</desc>"
    '<rect width="800" height="420" fill="#14215A"/></svg>'
)


def item(title, link, date="Thu, 15 Oct 2026 00:00:00 GMT", cover=None):
    slug = link.rstrip("/").rsplit("/", 1)[-1]
    url = escape(cover or COVER_URL.format(slug), {'"': "&quot;"})
    media = "" if cover == "" else f'<media:content url="{url}" medium="image"/>'
    pub = f"<pubDate>{date}</pubDate>" if date else ""
    return (
        f"<item><title>{title}</title><link>{escape(link)}</link>"
        f"<description>About  {title}.</description>{pub}{media}</item>"
    )


def feed(*items):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><title>Articles</title>'
        + "".join(items)
        + "</channel></rss>"
    )


FEED = feed(
    item("Write in Obsidian, Publish on Your Own Site", "https://brunosouzas.com/blog/write-in-obsidian/"),
    item(
        "When AI Writes the Code, the Engineer&apos;s Work Moves",
        "https://brunosouzas.com/blog/where-the-work-moves/",
        "Sun, 27 Sep 2026 00:00:00 GMT",
    ),
    item("Third", "https://brunosouzas.com/blog/third/", "Fri, 04 Sep 2026 00:00:00 GMT"),
)

README = """# Title

<!-- articles:start -->
old entry
<!-- articles:end -->

Footer.
"""


class ParseFeed(unittest.TestCase):
    def test_reads_title_link_date_and_cover(self):
        first = ua.parse_feed(FEED)[0]
        self.assertEqual(first.title, "Write in Obsidian, Publish on Your Own Site")
        self.assertEqual(first.link, "https://brunosouzas.com/blog/write-in-obsidian/")
        self.assertEqual(first.date, "15 Oct, 2026")
        self.assertEqual(first.cover, "https://brunosouzas.com/_astro/write-in-obsidian-card.abc123.svg")
        self.assertEqual(first.description, "About Write in Obsidian, Publish on Your Own Site.")
        self.assertEqual(first.slug, "write-in-obsidian")

    def test_decodes_entities_and_drops_leading_zero(self):
        articles = ua.parse_feed(FEED)
        self.assertEqual(articles[1].title, "When AI Writes the Code, the Engineer's Work Moves")
        self.assertEqual(articles[2].date, "4 Sep, 2026")

    def test_keeps_feed_order_up_to_limit(self):
        self.assertEqual([a.slug for a in ua.parse_feed(FEED, limit=2)], ["write-in-obsidian", "where-the-work-moves"])

    def test_collapses_whitespace_in_titles(self):
        self.assertEqual(ua.parse_feed(feed(item("Real\n\n  title", "https://brunosouzas.com/blog/t/")))[0].title, "Real title")

    def test_rejects_feeds_it_cannot_trust(self):
        cases = {
            "empty": "<rss><channel></channel></rss>",
            "not rss": "<html><body/></html>",
            "no date": feed(item("T", "https://brunosouzas.com/blog/t/", date="")),
            "no cover": feed(item("T", "https://brunosouzas.com/blog/t/", cover="")),
            "link elsewhere": feed(item("T", "https://evil.example/blog/t/")),
            "plain http": feed(item("T", "http://brunosouzas.com/blog/t/")),
            "lookalike host": feed(item("T", "https://brunosouzas.com.evil.example/t/")),
            "unsafe link": feed(item("T", 'https://brunosouzas.com/blog/t"onerror=x/')),
            "no slug": feed(item("T", "https://brunosouzas.com/blog/Bad_Slug/")),
            "cover elsewhere": feed(item("T", "https://brunosouzas.com/blog/t/", cover="https://evil.example/c.svg")),
        }
        for case, text in cases.items():
            with self.subTest(case), self.assertRaises(ValueError):
                ua.parse_feed(text)


class ThumbnailFile(unittest.TestCase):
    def test_draws_one_thumbnail(self):
        article = ua.parse_feed(FEED)[0]
        name, svg = ua.thumbnail_file(article, COVER_SVG)
        self.assertEqual(name, "write-in-obsidian.svg")
        self.assertIn("Cover: Write in Obsidian", svg)

    def test_rejects_a_cover_that_would_not_render(self):
        article = ua.parse_feed(FEED)[0]
        with self.assertRaises(ValueError):
            ua.thumbnail_file(article, COVER_SVG.replace("<rect", '<image href="https://evil.example/x.png"/><rect'))

    def test_rejects_a_cover_that_hides_markup_in_a_dtd_entity(self):
        article = ua.parse_feed(FEED)[0]
        cover = (
            '<!DOCTYPE svg [<!ENTITY x "&#60;script&#62;alert(1)&#60;/script&#62;'
            "&#60;image &#104;ref='https://evil.example/a.png'/&#62;\">]>"
            + COVER_SVG.replace("</svg>", "&x;</svg>")
        )
        self.assertEqual(ua.ba.problems(cover), [])  # the raw text looks clean
        with self.assertRaises(ValueError):
            ua.thumbnail_file(article, cover)


class FinalUrl(unittest.TestCase):
    def test_accepts_a_redirect_within_the_site(self):
        ua.check_final_url("https://brunosouzas.com/rss.xml", "https://brunosouzas.com/rss.xml/")

    def test_rejects_a_redirect_away_from_the_site(self):
        for final in ("https://evil.example/c.svg", "http://brunosouzas.com/c.svg"):
            with self.subTest(final=final), self.assertRaises(ValueError):
                ua.check_final_url("https://brunosouzas.com/_astro/c.svg", final)


class Render(unittest.TestCase):
    def test_one_row_per_article_with_thumbnail_title_date_and_description(self):
        block = ua.render(ua.parse_feed(FEED, limit=1))
        link = "https://brunosouzas.com/blog/write-in-obsidian/"
        self.assertEqual(
            block,
            f'<p><a href="{link}"><img align="left" width="200" src="assets/articles/write-in-obsidian.svg" '
            'alt="Cover: Write in Obsidian, Publish on Your Own Site"></a>'
            f'<a href="{link}"><b>Write in Obsidian, Publish on Your Own Site</b></a><br>'
            "<sub>15 Oct, 2026</sub><br>About Write in Obsidian, Publish on Your Own Site."
            '<br clear="left"></p>',
        )

    def test_separates_rows_with_a_rule(self):
        self.assertEqual(ua.render(ua.parse_feed(FEED, limit=3)).count("\n<hr>\n"), 2)

    def test_leaves_out_an_empty_description(self):
        article = ua.Article("T", "https://brunosouzas.com/blog/t/", "1 Jan, 2026", COVER_URL)
        self.assertIn('<sub>1 Jan, 2026</sub><br clear="left"></p>', ua.render([article]))

    def test_escapes_html_in_titles(self):
        article = ua.Article('<b>"x"</b>', "https://brunosouzas.com/blog/x/", "1 Jan, 2026", COVER_URL, "<i>d</i>")
        block = ua.render([article])
        self.assertIn('alt="Cover: &lt;b&gt;&quot;x&quot;&lt;/b&gt;"', block)
        self.assertIn("<b>&lt;b&gt;&quot;x&quot;&lt;/b&gt;</b>", block)
        self.assertIn('<br>&lt;i&gt;d&lt;/i&gt;<br clear="left"></p>', block)


class ReplaceBlock(unittest.TestCase):
    def test_replaces_only_the_block(self):
        updated = ua.replace_block(README, "new entry")
        self.assertIn("<!-- articles:start -->\nnew entry\n<!-- articles:end -->", updated)
        self.assertNotIn("old entry", updated)
        self.assertTrue(updated.startswith("# Title\n"))
        self.assertTrue(updated.endswith("\n\nFooter.\n"))

    def test_is_stable_when_run_twice(self):
        once = ua.replace_block(README, "new entry")
        self.assertEqual(ua.replace_block(once, "new entry"), once)

    def test_requires_both_markers(self):
        with self.assertRaises(ValueError):
            ua.replace_block("no markers here", "x")


class Update(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.readme = Path(self.tmp.name) / "README.md"
        self.readme.write_text(README, encoding="utf-8")
        self.thumbs = Path(self.tmp.name) / "articles"
        self.fetched = []

    def tearDown(self):
        self.tmp.cleanup()

    def get(self, url):
        self.fetched.append(url)
        return COVER_SVG

    def test_writes_thumbnails_and_readme_then_nothing_on_a_second_run(self):
        changed = ua.update(FEED, self.readme, self.thumbs, limit=2, get=self.get)
        self.assertIn("README.md", changed)
        self.assertEqual(len(list(self.thumbs.glob("*.svg"))), 2)
        self.assertEqual(len(self.fetched), 2)
        self.assertIn("assets/articles/where-the-work-moves.svg", self.readme.read_text(encoding="utf-8"))
        self.assertEqual(ua.update(FEED, self.readme, self.thumbs, limit=2, get=self.get), [])

    def test_removes_the_thumbnails_of_articles_that_left_the_list(self):
        ua.update(FEED, self.readme, self.thumbs, limit=2, get=self.get)
        changed = ua.update(FEED, self.readme, self.thumbs, limit=1, get=self.get)
        self.assertIn("assets/articles/where-the-work-moves.svg (removed)", changed)
        self.assertEqual([p.name for p in self.thumbs.glob("*.svg")], ["write-in-obsidian.svg"])

    def test_leaves_everything_untouched_when_a_cover_fetch_fails(self):
        def failing(url):
            raise OSError("network down")

        with self.assertRaises(OSError):
            ua.update(FEED, self.readme, self.thumbs, get=failing)
        self.assertEqual(self.readme.read_text(encoding="utf-8"), README)
        self.assertFalse(self.thumbs.exists())

    def test_leaves_everything_untouched_when_a_cover_is_unsafe(self):
        with self.assertRaises(ValueError):
            ua.update(FEED, self.readme, self.thumbs, get=lambda url: "<svg><script>x()</script></svg>")
        self.assertEqual(self.readme.read_text(encoding="utf-8"), README)
        self.assertFalse(self.thumbs.exists())


if __name__ == "__main__":
    unittest.main()
