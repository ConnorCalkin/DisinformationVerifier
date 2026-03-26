"""Functions for validating URLs, fetching HTML, and extracting article text."""

from urllib.parse import urlparse
import logging

import trafilatura
import validators


logger = logging.getLogger("URLScraper")


def validate_url(url: str) -> bool:
    """
    Checks if a string is a properly formatted, absolute URL.
    """
    # Basic structural check (checks for http/https, domain, etc.)
    if not validators.url(url):
        return False

    # Explicitly check for web protocols only
    if not url.startswith(("http://", "https://")):
        return False

    # Fact-checking specific check: Ensure it has a scheme and netloc (e.g. example.com)
    parsed = urlparse(url)
    if not all([parsed.scheme, parsed.netloc]):
        return False

    return True


def fetch_html(url: str) -> str:
    """Handles the networking layer only."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.error("Network error: Could not download %s", url)
    return downloaded


def extract_content(html: str) -> str:
    """
    Takes HTML string, returns cleaned text.
    """
    return trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False
    )


def setup_logging() -> None:
    """
    Configures logging for the Lambda function. Logs will be sent to CloudWatch.
    """

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def scrape_article_text(url: str) -> str:
    """
    Orchestrator function. Validates URL, fetches HTML, extracts content.
    """

    setup_logging()

    if not validate_url(url):
        logger.warning("Invalid URL: %s", url)
        raise ValueError(f"URL is not valid: {url}")

    html = fetch_html(url)
    if not html:
        raise ConnectionError(f"Failed to fetch content from: {url}")

    content = extract_content(html)
    if not content:
        logger.warning("Extraction failed for %s", url)
        raise ValueError(f"Failed to extract content from: {url}")

    return content
