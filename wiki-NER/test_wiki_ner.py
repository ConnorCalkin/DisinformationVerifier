# pylint: skip-file
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
import wiki_ner

# --- 1. CONFIGURATION & RESET ---


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Resets globals and sets env vars before every single test."""
    wiki_ner._CACHED_SECRET = None
    wiki_ner._OPENAI_CLIENT = None
    monkeypatch.setenv("SECRET_ID", "test-secret")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")

# --- 2. HAPPY PATHS ---


@patch("wiki_ner.extract_wiki_terms_from_claims")
@patch("wiki_ner.resolve_wiki_titles")
@patch("wiki_ner.wiki_api.page")
def test_lambda_handler_success(mock_page_factory, mock_resolve, mock_extract):
    # 1. Setup basic mocks
    mock_extract.return_value = ["Mars"]
    mock_resolve.return_value = ["Mars"]

    # 2. Create the page mock
    mock_page = MagicMock()

    # .exists() is a METHOD call: await page.exists()
    mock_page.exists = AsyncMock(return_value=True)

    # .sections, .fullurl, and .summary are PROPERTIES being awaited
    # We use PropertyMock to return an AsyncMock's return value
    type(mock_page).sections = PropertyMock(
        return_value=AsyncMock(return_value=[])())
    type(mock_page).fullurl = PropertyMock(
        return_value=AsyncMock(return_value="https://url.com")())
    type(mock_page).summary = PropertyMock(
        return_value=AsyncMock(return_value="Summary text")())

    mock_page_factory.return_value = mock_page

    # 3. Execute
    event = {"claims": ["Water on Mars"]}
    response = wiki_ner.lambda_handler(event, {})

    # 4. Assert
    assert response["statusCode"] == 200
    assert "Summary text" in response["body"]

# --- 3. EDGE CASES  ---


@pytest.mark.parametrize("invalid_event", [{}, {"claims": []}, {"claims": None}])
def test_handler_rejects_bad_input(invalid_event):
    """Verifies the guardrails for missing or null input."""
    response = wiki_ner.lambda_handler(invalid_event, None)
    assert response["statusCode"] == 400


@patch("wiki_ner.get_openai_client")
def test_llm_garbage_parsing(mock_client):
    """Verifies that the LLM returning non-JSON text doesn't crash the code."""
    mock_client.return_value.chat.completions.create.return_value.choices[
        0].message.content = "I am a pirate, not a JSON!"

    terms = wiki_ner.extract_wiki_terms_from_claims(["Test"])
    assert terms == []  # Should recover and return empty list


@pytest.mark.asyncio  # If using pytest-asyncio
@patch("wiki_ner.wiki_api.page")
async def test_wikipedia_page_missing(mock_page):
    """Verifies that 404s from Wikipedia are handled without errors."""

    # Configure the mock to return an object where .exists() is an AsyncMock
    mock_exists = AsyncMock(return_value=False)
    mock_page.return_value.exists = mock_exists

    # Await the function call
    result = await wiki_ner.fetch_article_body("Atlantis", ["ocean"])

    assert result == {}
    mock_exists.assert_awaited_once()


@patch("wiki_ner.sm_client.get_secret_value")
def test_aws_infrastructure_failure(mock_sm):
    """Verifies the 500 error catch-all when AWS is unreachable."""
    mock_sm.side_effect = Exception("Connection Timeout")

    response = wiki_ner.lambda_handler({"claims": ["Test"]}, None)
    assert response["statusCode"] == 500
    assert "Internal research engine error" in response["body"]
