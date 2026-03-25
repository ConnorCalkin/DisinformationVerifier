import pytest
import json
from unittest.mock import MagicMock, patch
import wiki_ner

# --- 1. CONFIGURATION & RESET ---

@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Resets globals and sets env vars before every single test."""
    wiki_ner._CACHED_SECRET = None
    wiki_ner._OPENAI_CLIENT = None
    monkeypatch.setenv("SECRET_ID", "test-secret")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")

# --- 2. SUCCESS CASE  ---

@patch("wiki_ner.sm_client.get_secret_value")
@patch("wiki_ner.OpenAI")
@patch("wiki_ner.wikipedia.search")
@patch("wiki_ner.wiki_api.page")
def test_full_pipeline_success(mock_page, mock_search, mock_oa, mock_sm):
    # Setup Mocks with Placeholder Data
    mock_sm.return_value = {'SecretString': json.dumps({'OPENAI_API_KEY': 'sk-test'})}
    mock_oa.return_value.chat.completions.create.return_value.choices[0].message.content = \
        json.dumps({"search_terms": ["Eiffel Tower"]})
    mock_search.return_value = ["Eiffel Tower"]
    
    p = MagicMock()
    p.exists.return_value = True
    p.summary = "A tower in Paris."
    p.fullurl = "https://wiki.com/eiffel"
    p.sections = [MagicMock(title="History", text="Built in 1887")]
    mock_page.return_value = p

    response = wiki_ner.lambda_handler({"claims": ["Paris has a tower"]}, None)
    
    assert response["statusCode"] == 200
    assert "Eiffel Tower" in response["body"]

# --- 3. EDGE CASES  ---

@pytest.mark.parametrize("invalid_event", [{}, {"claims": []}, {"claims": None}])
def test_handler_rejects_bad_input(invalid_event):
    """Verifies the guardrails for missing or null input."""
    response = wiki_ner.lambda_handler(invalid_event, None)
    assert response["statusCode"] == 400

@patch("wiki_ner.get_openai_client")
def test_llm_garbage_parsing(mock_client):
    """Verifies that the LLM returning non-JSON text doesn't crash the code."""
    mock_client.return_value.chat.completions.create.return_value.choices[0].message.content = "I am a pirate, not a JSON!"
    
    terms = wiki_ner.extract_wiki_terms_from_claims(["Test"])
    assert terms == [] # Should recover and return empty list

@patch("wiki_ner.wiki_api.page")
def test_wikipedia_page_missing(mock_page):
    """Verifies that 404s from Wikipedia are handled without errors."""
    mock_page.return_value.exists.return_value = False
    
    result = wiki_ner.fetch_article_body("Atlantis", ["ocean"])
    assert result == {} # Should return empty dict for non-existent page

@patch("wiki_ner.sm_client.get_secret_value")
def test_aws_infrastructure_failure(mock_sm):
    """Verifies the 500 error catch-all when AWS is unreachable."""
    mock_sm.side_effect = Exception("Connection Timeout")
    
    response = wiki_ner.lambda_handler({"claims": ["Test"]}, None)
    assert response["statusCode"] == 500
    assert "Internal research engine error" in response["body"]