import feedparser
import trafilatura
import json

FEEDS = {
    "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters": "https://ir.thomsonreuters.com/rss/news-releases.xml?items=5",
    "FullFact": "https://fullfact.org/feed/"
}


def harvest_news():

    all_articles = []

    for source, url in FEEDS.items():
        print(f"Parsing {source}...")
        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:
            link = entry.link

            downloaded = trafilatura.fetch_url(link)
            body_text = trafilatura.extract(downloaded)

            if body_text:
                all_articles.append({
                    "source": source,
                    "title": entry.title,
                    "url": link,
                    "content": body_text,
                    "timestamp": entry.published if 'published' in entry else None
                })

    return all_articles


# To test:
data = harvest_news()
print(json.dumps(data, indent=2))
