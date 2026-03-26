# pylint: skip-file

from unittest.mock import patch

import pytest
from url_scraper import validate_url, extract_content, fetch_html, scrape_article_text


# Testing Validation Logic (Pure Function)

def test_validate_url_success():
    """Verify that valid protocols pass."""

    assert validate_url("https://www.bbc.com/news/world") is True
    assert validate_url("http://example.com") is True


def test_validate_url_failure():
    """Verify that garbage strings or missing protocols fail."""

    assert validate_url("not-a-url") is False
    assert validate_url("") is False


# 2. Testing Extraction Logic

def test_extract_content_functionality():
    """
    Tests the logic of trafilatura by passing raw HTML.
    This avoids mocking while still being a 'pure' logic test.
    """
    sample_html = """
    <html>
        <body>
            <article>
                <h1>Breaking News</h1>
                <p>This is a claim that needs fact-checking.</p>
            </article>
        </body>
    </html>
    """
    result = extract_content(sample_html)
    assert "This is a claim" in result
    assert "Breaking News" in result


# Testing the Full Orchestrator

def test_scrape_article_text():
    """
    Tests the full flow by mocking the network call. 
    The extraction logic still runs on the 'fake' HTML.
    """

    test_url = "https://www.fakestory.com/article-1"

    # The "fake" HTML for scraper to process:
    fake_html = """
    <html>
        <body>
            <h1>The Moon is Made of Cheese</h1>
            <p>Scientists have discovered the moon is actually cheddar.</p>
        </body>
    </html>
    """

    # Patch the fetch_url function inside the url_scraper module
    with patch("url_scraper.trafilatura.fetch_url") as mock_fetch:
        # Tell the mock to return fake_html
        mock_fetch.return_value = fake_html

        from url_scraper import scrape_article_text
        result = scrape_article_text(test_url)

        # Assertions
        assert "The Moon is Made of Cheese" in result
        assert "cheddar" in result
        # Verify that the network was actually "called" once with the right URL
        mock_fetch.assert_called_once_with(test_url)


def test_scrape_article_text_invalid_url():
    """Ensures the orchestrator returns an empty string on bad input."""
    with pytest.raises(ValueError):
        scrape_article_text("htpt://bad-url")
