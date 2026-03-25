"""provides functions for scraping news articles from specified RSS feeds"""

import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import trafilatura
from bs4 import BeautifulSoup


logger = logging.getLogger("NewsScraper")

# Each RSS feed to search for new srticles:
FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters": "https://ir.thomsonreuters.com/rss/news-releases.xml?items=100",
    "FullFact": "https://fullfact.org/feed/"
}


# How far to look back at articles in hours:
SCRAPE_FREQUENCY = 3


def fetch_raw_html(url: str) -> str:
    """
    Downloads HTML and handles network-level errors.
    """

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.error("Failed to download content from: %s", url)
        raise ConnectionError(f"Could not reach {url}")
    return downloaded


def handle_nested_content(url: str, html: str) -> str:
    """
    Evaluates page content for site-specific 'thin' pages and resolves redirects.

    If the content (e.g., Reuters Investor Relations) is under 200 characters, 
    this attempts to locate and fetch the full article from a nested link 
    to prevent indexing empty summary pages.
    """

    # Only reuters pages have this potential issue.
    if "ir.thomsonreuters.com" not in url:
        return html

    current_content = trafilatura.extract(html)
    content_len = len(current_content) if current_content else 0

    # If enough content is present, return as is.
    if content_len >= 200:
        return html

    logger.info(
        "Content too short (%s chars). Searching for redirect link...", content_len)

    # Extraction: Parse DOM to find the 'Full Release' link container, using BeautifulSoup.
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.find("div", class_="full-release-body")
    if not container:
        return html

    link_tag = container.find("a", href=True)
    if not link_tag:
        return html

    # Avoid infinite loops by ensuring we aren't redirecting to the same URL
    new_url = urljoin(url, link_tag['href'])
    if new_url == url:
        return html

    logger.debug("Reuters page met length requirements or no link found.")
    return fetch_raw_html(new_url)


def get_content_body(url: str) -> str:
    """
    Orchestrates the download, special case handling, and extraction.
    """

    logger.info("Fetching content from: %s", url)

    raw_html = fetch_raw_html(url)

    final_html = handle_nested_content(url, raw_html)

    try:
        content = trafilatura.extract(final_html)
    except Exception as e:
        logger.warning("Failed to extract content from %s: %s", url, str(e))
        return ""

    return content


def is_recent_article(entry, cutoff_hours: int) -> bool:
    """
    Checks if the article is recent enough to be scraped.
    """

    if not hasattr(entry, 'published_parsed'):
        logger.warning("Entry missing 'published_parsed': %s",
                       getattr(entry, 'title', 'No Title'))
        return False

    published_dt = datetime.fromtimestamp(
        time.mktime(entry.published_parsed), tz=timezone.utc
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cutoff_hours)
    return published_dt > cutoff


def transform_entry(source: str, entry) -> dict:
    """
    Converts RSS entry to a consistent dict format, including content extraction.
    """

    content = get_content_body(entry.link)
    if not content:
        return {}

    return {
        "source": source,
        "title": getattr(entry, 'title', 'No Title'),
        "url": entry.link,
        "content": content,
        "timestamp": datetime.fromtimestamp(
            time.mktime(entry.published_parsed), tz=timezone.utc
        ).isoformat()
    }


def process_feed_entries(source: str, url: str, hours: int):
    """
    Generator that yields valid, recent articles from a single feed.
    """

    feed = feedparser.parse(url)

    for entry in feed.entries:
        if not is_recent_article(entry, hours):
            continue

        article = transform_entry(source, entry)
        if article:
            yield article


def get_recent_content(feeds: dict, hours: int) -> list[dict]:
    """
    Coordinates the scraping process using the generator.
    """

    new_articles = []

    for source, url in feeds.items():
        logger.info(f"Checking RSS feed: {source}")

        for article in process_feed_entries(source, url, hours):
            new_articles.append(article)
            logger.info(f"Scraped: {article['title']}")

    return new_articles


def setup_logging():
    """
    Configures logging for the Lambda function. Logs will be sent to CloudWatch.
    """

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def run():
    """
    Main function to execute the RSS scraping process. 
    """

    setup_logging()
    logger.info("Starting RSS scrape...")
    articles = get_recent_content(FEEDS, SCRAPE_FREQUENCY)
    logger.info(f"Scraped {len(articles)} new articles.")
