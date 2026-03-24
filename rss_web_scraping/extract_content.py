"""provides functions for harvesting news articles from specified RSS feeds"""

import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser
import trafilatura
from bs4 import BeautifulSoup


logger = logging.getLogger("extract_content")

FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters": "https://ir.thomsonreuters.com/rss/news-releases.xml?items=100",
    "FullFact": "https://fullfact.org/feed/"
}

# How far to look back at articles in hours.
SCRAPE_FREQUENCY = 1


def get_content_body(url):
    """
    Uses links to scrape the full content of the article.
    """
    logger.info(f"Fetching content from: {url}")
    downloaded = trafilatura.fetch_url(url)

    if not downloaded:
        logger.warning(f"Failed to download content from {url}")
        return None

    if "ir.thomsonreuters.com" in url:
        soup = BeautifulSoup(downloaded, 'html.parser')
        container = soup.find("div", class_="full-release-body")

        if container:
            link_tag = container.find("a", href=True)
            if link_tag:
                new_url = urljoin(url, link_tag['href'])
                logger.info(f"Redirecting from landing page to: {new_url}")
                downloaded = trafilatura.fetch_url(new_url)

    content = trafilatura.extract(downloaded)
    if not content:
        logger.warning(f"Trafilatura could not extract text from {url}")

    return content


def get_recent_content():
    """
    Harvest news articles from specified RSS feeds and return metadata.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=SCRAPE_FREQUENCY)
    new_articles = []

    for source, url in FEEDS.items():
        logger.info(f"Checking RSS feed: {source}")
        feed = feedparser.parse(url)

        for entry in feed.entries:
            if hasattr(entry, 'published_parsed'):
                published_dt = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc)

                if published_dt > cutoff:
                    logger.info(f"New article found: {entry.title}")
                    content = get_content_body(entry.link)

                    if content:
                        new_articles.append({
                            "source": source,
                            "title": entry.title,
                            "url": entry.link,
                            "content": content,
                            "timestamp": published_dt.isoformat()
                        })
                    else:
                        logger.warning(
                            f"Skipping article due to empty content: {entry.title}")

    return new_articles


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(message)s'
    )

    logger.info("Starting news harvest...")
    articles = get_recent_content()
    logger.info(f"Harvested {len(articles)} new articles.")
