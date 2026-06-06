from semi_news_collector.store import SeenStore


def test_seen_store_marks_items(tmp_path):
    db_path = tmp_path / "seen.sqlite3"
    with SeenStore(str(db_path)) as store:
        assert not store.has_seen("abc")
        store.mark_seen("abc", "Title", "https://example.com")
        assert store.has_seen("abc")
