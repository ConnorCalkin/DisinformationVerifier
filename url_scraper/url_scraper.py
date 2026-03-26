from typing import Optional
import logging
import trafilatura
from urllib.parse import urlparse
import validators

logger = logging.getLogger("URLExtractor")


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


def fetch_html(url: str) -> Optional[str]:
    """Handles the networking layer only."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.error(f"Network error: Could not download {url}")
    return downloaded


def extract_content(html: str) -> Optional[str]:
    """
    Takes HTML string, returns cleaned text.
    """
    return trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False
    )


def scrape_article_text(url: str) -> str:
    """
    Orchestrator function. Validates URL, fetches HTML, extracts content.
    """

    if not validate_url(url):
        logger.warning(f"Invalid URL: {url}")
        raise ValueError(f"URL is not valid: {url}")

    html = fetch_html(url)
    if not html:
        raise ConnectionError(f"Failed to fetch content from: {url}")

    content = extract_content(html)
    if not content:
        logger.warning(f"Extraction failed for {url}")
        raise ValueError(f"Failed to extract content from: {url}")

    return content


print(scrape_article_text(
    "https://www.gbnews.com/science/archaeology-breakthrough-medieval-600-year-old-grape-seed-found-french-toilet"))


print(scrape_article_text(
    "https://www.aljazeera.com/sports/2026/3/26/nba-owners-vote-to-explore-seattle-las-vegas-expansion-bids"))
