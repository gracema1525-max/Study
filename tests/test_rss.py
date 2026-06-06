from semi_news_collector.rss import collect_feed


def test_collect_feed_filters_keywords(tmp_path):
    feed = """
    <rss version="2.0"><channel><title>Test Feed</title>
      <item><title>TSMC expands CoWoS capacity</title><link>https://example.com/a</link><description>Advanced packaging for AI chips.</description><pubDate>Sat, 01 Jun 2024 00:00:00 GMT</pubDate></item>
      <item><title>Unrelated consumer gadget</title><link>https://example.com/b</link><description>No relevant words.</description></item>
    </channel></rss>
    """
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(feed, encoding="utf-8")

    items = collect_feed(feed_path.as_uri(), ["TSMC", "HBM"], max_items=10)

    assert len(items) == 1
    assert items[0].title == "TSMC expands CoWoS capacity"
    assert items[0].matched_keywords == ("TSMC",)
