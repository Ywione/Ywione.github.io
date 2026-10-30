import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('feed', Path(__file__).resolve().parents[1] / 'scripts/fetch_substack.py')
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

class FeedTests(unittest.TestCase):
    def test_realistic_feed_and_ordering(self):
        posts = feed.parse_feed(b'''<rss><channel>
        <item><title>Older &amp; valid</title><link>https://ywione.substack.com/p/older</link><pubDate>Tue, 27 Oct 2026 09:00:00 GMT</pubDate><description><![CDATA[<p>One &amp; two</p><p>Three</p><script>hidden()</script>]]></description></item>
        <item><title>Latest</title><link>https://ywione.substack.com/p/latest</link><pubDate>Fri, 30 Oct 2026 09:00:00 GMT</pubDate></item>
        <item><title>Duplicate</title><link>https://ywione.substack.com/p/latest</link></item>
        <item><title>Bad link</title><link>javascript:alert(1)</link></item>
        </channel></rss>''')
        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0]['title'], 'Latest')
        self.assertEqual(posts[0]['summary'], '')
        self.assertEqual(posts[1]['title'], 'Older & valid')
        self.assertEqual(posts[1]['summary'], 'One & two Three')

    def test_bad_date_does_not_discard_article(self):
        posts = feed.parse_feed(b'<rss><channel><item><title>Post</title><link>https://ywione.substack.com/p/post</link><pubDate>invalid</pubDate></item></channel></rss>')
        self.assertEqual(posts[0]['date'], None)

    def test_empty_feed_and_invalid_response(self):
        self.assertEqual(feed.parse_feed(b'<rss><channel/></rss>'), [])
        with self.assertRaises(ValueError):
            feed.parse_feed(b'<html/>')

    def test_fetch_failure_preserves_saved_data(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'substack.json'
            target.write_text('{"posts": [{"title": "Saved"}]}')
            def failing(*args, **kwargs):
                raise OSError('Network unavailable')
            with self.assertRaises(OSError):
                feed.refresh(target, failing)
            self.assertEqual(target.read_text(), '{"posts": [{"title": "Saved"}]}')

    def test_summaries_have_bounded_length(self):
        self.assertLessEqual(len(feed.clean('word ' * 500)), 280)
        self.assertEqual(feed.clean('<p>2 &lt; 3</p>'), '2 < 3')

if __name__ == '__main__':
    unittest.main()
