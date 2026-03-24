import feedparser
import trafilatura
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import time
from urllib.parse import urljoin

FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters": "https://ir.thomsonreuters.com/rss/news-releases.xml?items=100",
    "FullFact": "https://fullfact.org/feed/"
}

# How far to look back at articles in hours.
SCRAPE_FREQUENCY = 1


def get_content_body(url):
    """
    Uses links to scrape the full content of the article, 
    even if the initial URL is a landing page with a link to the actual article.
    """

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None

    if "ir.thomsonreuters.com" in url:
        soup = BeautifulSoup(downloaded, 'html.parser')

        container = soup.find("div", class_="full-release-body")
        if container:
            link_tag = container.find("a", href=True)
            if link_tag:
                new_url = urljoin(url, link_tag['href'])
                print(f"Redirecting from landing page to: {new_url}")
                # Fetch the actual content from the redirected URL
                downloaded = trafilatura.fetch_url(new_url)

    return trafilatura.extract(downloaded)


def get_recent_content():
    """
    Harvest news articles from specified RSS feeds, extract their content, and return a list of articles with metadata.
    """

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=SCRAPE_FREQUENCY)

    new_articles = []

    for source, url in FEEDS.items():
        feed = feedparser.parse(url)

        for entry in feed.entries:
            print(f"Processing article: {entry.title}")
            # feedparser converts dates to a 9-tuple time structure
            # convert that back to a datetime object for easy comparison
            if hasattr(entry, 'published_parsed'):
                published_dt = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc)

                if published_dt > cutoff:
                    print(f"New article found: {entry.title}")
                    content = get_content_body(entry.link)

                    if content:
                        new_articles.append({
                            "source": source,
                            "title": entry.title,
                            "url": entry.link,
                            "content": content,
                            "timestamp": published_dt.isoformat()
                        })
    return new_articles


if __name__ == "__main__":
    articles = get_recent_content()
    print(f"Harvested {len(articles)} new articles.")
    print(articles)
