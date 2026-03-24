import pytest
from datetime import datetime, timezone, timedelta
from extract_content import get_content_body, get_recent_content


class MockEntry:
    def __init__(self, title, link, published_parsed):
        self.title = title
        self.link = link
        self.published_parsed = published_parsed


# --- Tests for get_content_body ---

def test_get_content_body_none(monkeypatch):
    """Test that it returns None when download fails."""
    monkeypatch.setattr("trafilatura.fetch_url", lambda url: None)
    assert get_content_body("https://example.com") is None


def test_get_content_body_extraction(monkeypatch):
    """Test successful extraction"""
    monkeypatch.setattr("trafilatura.fetch_url",
                        lambda url: "<html><body>Content</body></html>")
    monkeypatch.setattr("trafilatura.extract", lambda html: "Clean Content")

    result = get_content_body("https://example.com")
    assert result == "Clean Content"


# --- Tests for get_recent_content ---

def test_get_recent_content_filters_old_articles(monkeypatch):
    """
    Test that articles older than SCRAPE_FREQUENCY are ignored.
    No complex mocking, just replacing the feedparser return value.
    """
    # 1. Setup times: one recent, one old
    now_struct = datetime.now(timezone.utc).timetuple()
    old_struct = (datetime.now(timezone.utc) - timedelta(hours=5)).timetuple()

    mock_feed = type('obj', (object,), {
        'entries': [
            MockEntry("New Article", "http://test.com/new", now_struct),
            MockEntry("Old Article", "http://test.com/old", old_struct)
        ],
        'bozo': 0
    })

    # 2. Patch the feedparser and the content downloader
    monkeypatch.setattr("feedparser.parse", lambda url: mock_feed)
    monkeypatch.setattr("extract_content.get_content_body",
                        lambda url: "Some content")

    # 3. Execute
    articles = get_recent_content()

    # 4. Assert
    # 3 feeds in your FEEDS dict * 1 new article each
    assert len(articles) == 3
    assert articles[0]["title"] == "New Article"
    # Ensure "Old Article" was skipped
    assert not any(a["title"] == "Old Article" for a in articles)


@pytest.mark.parametrize("source,url", [
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters", "https://ir.thomsonreuters.com/rss/news-releases.xml?items=100")
])
def test_feeds_dictionary_integrity(source, url):
    """Ensure our FEEDS mapping stays correct."""
    from extract_content import FEEDS
    assert FEEDS[source] == url
