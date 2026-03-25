# pylint: skip-file

import pytest
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import extract_content as scraper

# --- HELPERS ---


@dataclass
class MockEntry:
    """A simple container to mimic a feedparser entry without MagicMock."""
    link: str = "http://example.com"
    title: str = "Test Title"
    published_parsed: time.struct_time = None

# --- TESTS ---


def test_is_recent_article_logic():
    """Tests the time filtering using real time structs, no mocks needed."""
    now_struct = time.gmtime()
    old_struct = time.gmtime(time.time() - (24 * 3600))  # 24 hours ago

    recent_entry = MockEntry(published_parsed=now_struct)
    old_entry = MockEntry(published_parsed=old_struct)

    assert scraper.is_recent_article(recent_entry, cutoff_hours=3) is True
    assert scraper.is_recent_article(old_entry, cutoff_hours=3) is False


def test_handle_nested_content_reuters_logic():
    """
    Tests the Reuters redirect logic by passing in HTML strings.
    No network mocking required because we test the decision logic.
    """
    reuters_url = "https://ir.thomsonreuters.com/news-123"

    # Scenario 1: Content is already long enough (> 200 chars)
    long_html = "<div>" + ("Content " * 50) + "</div>"
    # It should return the same HTML immediately without looking for links
    assert scraper.handle_nested_content(reuters_url, long_html) == long_html

    # Scenario 2: Content is short but NO redirect link exists
    short_no_link = "<div>Too short</div>"
    assert scraper.handle_nested_content(
        reuters_url, short_no_link) == short_no_link


def test_transform_entry_structure():
    """
    Tests that transform_entry correctly builds the dictionary.
    We 'monkeypatch' the heavy network call with a simple lambda for speed.
    """
    now = time.gmtime()
    entry = MockEntry(link="http://test.com",
                      title="Hello", published_parsed=now)

    # We briefly swap the heavy fetcher for a simple string return
    # This is 'incredibly simple' mocking as requested.
    pytest.monkeypatch = pytest.MonkeyPatch()
    pytest.monkeypatch.setattr(
        scraper, "get_content_body", lambda x: "Article Body")

    result = scraper.transform_entry("BBC", entry)

    assert result["source"] == "BBC"
    assert result["title"] == "Hello"
    assert result["content"] == "Article Body"
    assert "timestamp" in result


def test_feeds_configuration():
    """Ensure the feed list is valid and points to HTTPS."""
    for source, url in scraper.FEEDS.items():
        assert url.startswith("https://")
        assert len(source) > 0


@pytest.mark.parametrize("invalid_entry", [
    (MockEntry(published_parsed=None)),  # Missing date
    (object()),                          # Not even an entry object
])
def test_is_recent_article_edge_cases(invalid_entry):
    """Checks that the scraper doesn't crash on garbage data."""
    assert scraper.is_recent_article(invalid_entry, 3) is False
