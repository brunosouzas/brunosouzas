import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import update_articles as ua  # noqa: E402

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Articles</title>
<item><title>Write in Obsidian, Publish on Your Own Site</title>
<link>https://brunosouzas.com/blog/write-in-obsidian-publish-on-your-site/</link>
<pubDate>Thu, 15 Oct 2026 00:00:00 GMT</pubDate></item>
<item><title>When AI Writes the Code, the Engineer&apos;s Work Moves</title>
<link>https://brunosouzas.com/blog/where-the-work-moves/</link>
<pubDate>Sun, 27 Sep 2026 00:00:00 GMT</pubDate></item>
<item><title>Third</title><link>https://brunosouzas.com/blog/third/</link>
<pubDate>Fri, 04 Sep 2026 00:00:00 GMT</pubDate></item>
</channel></rss>"""

README = """# Title

Intro.

<!-- articles:start -->
- old entry
<!-- articles:end -->

Footer.
"""


class ParseFeed(unittest.TestCase):
    def test_reads_title_link_and_site_date(self):
        first = ua.parse_feed(FEED)[0]
        self.assertEqual(first.title, "Write in Obsidian, Publish on Your Own Site")
        self.assertEqual(first.link, "https://brunosouzas.com/blog/write-in-obsidian-publish-on-your-site/")
        self.assertEqual(first.date, "15 Oct, 2026")

    def test_decodes_entities_and_drops_leading_zero(self):
        articles = ua.parse_feed(FEED)
        self.assertEqual(articles[1].title, "When AI Writes the Code, the Engineer's Work Moves")
        self.assertEqual(articles[2].date, "4 Sep, 2026")

    def test_keeps_feed_order_up_to_limit(self):
        titles = [a.title for a in ua.parse_feed(FEED, limit=2)]
        self.assertEqual(len(titles), 2)
        self.assertTrue(titles[0].startswith("Write in Obsidian"))
        self.assertTrue(titles[1].startswith("When AI Writes"))

    def test_rejects_an_empty_feed(self):
        with self.assertRaises(ValueError):
            ua.parse_feed("<rss><channel></channel></rss>")

    def test_rejects_a_document_that_is_not_rss(self):
        with self.assertRaises(ValueError):
            ua.parse_feed("<html><body/></html>")


class Render(unittest.TestCase):
    def test_escapes_brackets_in_titles(self):
        line = ua.render([ua.Article("Arrays [and] lists", "https://x/", "1 Jan, 2026")])
        self.assertEqual(line, "- [Arrays \\[and\\] lists](https://x/) · 1 Jan, 2026")


class ReplaceBlock(unittest.TestCase):
    def test_replaces_only_the_block(self):
        updated = ua.replace_block(README, "- new entry")
        self.assertIn("<!-- articles:start -->\n- new entry\n<!-- articles:end -->", updated)
        self.assertNotIn("old entry", updated)
        self.assertTrue(updated.startswith("# Title\n\nIntro.\n"))
        self.assertTrue(updated.endswith("\n\nFooter.\n"))

    def test_is_stable_when_run_twice(self):
        once = ua.replace_block(README, "- new entry")
        self.assertEqual(ua.replace_block(once, "- new entry"), once)

    def test_requires_both_markers(self):
        with self.assertRaises(ValueError):
            ua.replace_block("no markers here", "- x")


class Main(unittest.TestCase):
    def test_writes_only_when_the_list_changed(self):
        import tempfile

        original_fetch = ua.fetch
        ua.fetch = lambda url: FEED
        try:
            with tempfile.TemporaryDirectory() as tmp:
                readme = Path(tmp) / "README.md"
                readme.write_text(README, encoding="utf-8")
                self.assertEqual(ua.main(["--readme", str(readme)]), 0)
                first = readme.read_text(encoding="utf-8")
                self.assertIn("Write in Obsidian", first)
                mtime = readme.stat().st_mtime_ns
                self.assertEqual(ua.main(["--readme", str(readme)]), 0)
                self.assertEqual(readme.stat().st_mtime_ns, mtime)
        finally:
            ua.fetch = original_fetch


if __name__ == "__main__":
    unittest.main()
