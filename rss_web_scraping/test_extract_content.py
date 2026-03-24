import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import extract_content as scraper


def test_is_recent_article():
    """Tests the time filtering logic with real time structs."""
    now_struct = time.gmtime()
    old_struct = time.gmtime(time.time() - (5 * 3600))  # 5 hours ago

    recent_entry = MagicMock(published_parsed=now_struct)
    old_entry = MagicMock(published_parsed=old_struct)

    assert scraper.is_recent_article(recent_entry, cutoff_hours=3) is True
    assert scraper.is_recent_article(old_entry, cutoff_hours=3) is False


def test_is_recent_article_missing_attr():
    """
    Edge case: entry is missing the date attribute.
    """

    bad_entry = MagicMock(spec=[])
    assert scraper.is_recent_article(bad_entry, 3) is False


def test_handle_special_cases_reuters_redirect(monkeypatch):
    """
    Verifies that Reuters short content triggers a secondary fetch.
    """

    # URL that matches "ir.thomsonreuters.com"
    reuters_url = "https://ir.thomsonreuters.com/news-123"

    short_html = '<div class="full-release-body"><a href="/full-article">Link</a></div>'
    full_content_html = "<html><body>" + \
        ("ha " * 101) + "</body></html>"  # Definitely > 200 chars

    # Track calls to ensure the second fetch actually happened
    fetch_calls = []

    def mock_fetch(url):
        fetch_calls.append(url)
        if "/full-article" in url:
            return full_content_html
        return short_html

    # Patch the function inside scraper module
    monkeypatch.setattr(scraper, "fetch_raw_html", mock_fetch)

    # 4. Mock trafilatura.extract to return something short for the first call
    # and something long for the second call.
    def mock_extract(html):
        if "full-release-body" in html:
            return "short"  # Triggers the < 200 char logic
        return "This is a very long string content " * 20

    monkeypatch.setattr("trafilatura.extract", mock_extract)

    result_html = scraper.handle_special_cases(reuters_url, short_html)

    assert result_html == full_content_html
    assert any(
        "/full-article" in url for url in fetch_calls), "The redirect URL was never fetched"


def test_get_content_body_success(monkeypatch):
    """Tests the orchestration of fetching and extracting."""
    monkeypatch.setattr(scraper, "fetch_raw_html",
                        lambda url: "<html>raw</html>")
    monkeypatch.setattr("trafilatura.extract", lambda html: "Clean Content")

    # handle_special_cases is a pass-through for non-reuters URLs
    result = scraper.get_content_body("https://bbc.com/news")
    assert result == "Clean Content"


def test_get_content_body_network_failure(monkeypatch):
    """Tests that a download failure raises the expected error."""
    monkeypatch.setattr("trafilatura.fetch_url", lambda url: None)
    with pytest.raises(ConnectionError):
        scraper.get_content_body("https://example.com")


def test_get_recent_content_integration(monkeypatch):
    """Tests the full loop from RSS to List of Dicts."""
    now_struct = time.gmtime()

    # 1. Mock the RSS feed response
    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(title="Test Art", link="http://test.com",
                  published_parsed=now_struct)
    ]
    monkeypatch.setattr("feedparser.parse", lambda url: mock_feed)

    # 2. Mock the content extraction so no real web calls happen
    monkeypatch.setattr(scraper, "get_content_body",
                        lambda url: "Article Body Content")

    # 3. Execute with a small subset of feeds
    test_feeds = {"Test": "http://test-rss.com"}
    results = scraper.get_recent_content(test_feeds, hours=1)

    assert len(results) == 1
    assert results[0]["source"] == "Test"
    assert results[0]["content"] == "Article Body Content"
    assert "timestamp" in results[0]


def test_feeds_dictionary_integrity():
    """Ensure FEEDS mapping exists and has expected keys."""
    assert "BBC" in scraper.FEEDS
    assert "Reuters" in scraper.FEEDS
    assert scraper.FEEDS["BBC"].startswith("http")
