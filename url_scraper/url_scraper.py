"""Functions for validating URLs, fetching HTML, and extracting article text."""

import json
from urllib.parse import urlparse
import logging

import trafilatura
import validators


logger = logging.getLogger("URLScraper")


def normalise_url(url: str) -> str:
    """
    Normalises a URL by adding 'http://' if missing.
    This allows users to input URLs in a more flexible way.
    """

    if url and not url.startswith(("http://", "https://")):
        logger.info(f"Normalising URL: adding https:// to {url}")
        url = "https://" + url
    return url


def validate_url(url: str) -> bool:
    """
    Validates a URL, supporting both full addresses and those starting with 'www'.
    """
    if not url:
        return False

    # 2. Structure check using the 'validators' library
    if not validators.url(url):
        return False

    # 3. Protocol & Netloc check
    parsed = urlparse(url)

    # Ensure it's web-based and has a domain (netloc)
    if parsed.scheme not in ["http", "https"] or not parsed.netloc:
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

    url = normalise_url(url)

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


def lambda_handler(event: dict, context: dict) -> dict:
    """
    Main entry point for the Lambda Function URL.
    """

    setup_logging()

    try:
        body_str = event.get("body", "{}")

        body = json.loads(body_str)
        target_url = body.get("url")

        if not target_url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No 'url' key found in request body"})
            }

        logger.info("Starting scrape for: %s", target_url)
        content = scrape_article_text(target_url)

        # 3. Return a successful response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "url": target_url,
                "text": content
            })
        }

    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    except RuntimeError as e:
        logger.error("Error during execution: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
