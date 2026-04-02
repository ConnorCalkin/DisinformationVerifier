"""Test suite for streamlit_functions.py. 
"""

import pytest
from unittest.mock import patch

from lambda_connection_utils import (send_url_to_web_scraping_lambda,
                                 send_claims_to_rag_lambda, send_claims_to_wiki_lambda,
                                 create_llm_prompt, validate_inputs_for_prompt,
                                 Claim)


@patch('requests.post')
def test_lambda_logic_simple_response(mock_post):

    lamba_url = "https://my-lambda.aws"

    mock_response = mock_post.return_value

    mock_response.json.return_value = {
        "text": "mock_text", "status_code": 200}

    mock_response.status_code = 200

    result = send_url_to_web_scraping_lambda("https://example.com", lamba_url)

    assert result == "mock_text"


@patch('requests.post')
def test_lambda_logic_bad_request(mock_post):

    lamba_url = "https://my-lambda.aws"

    mock_return = {"message": "error_message", "status_code": 400}

    mock_post.return_value.json.return_value = mock_return

    with pytest.raises(RuntimeError):
        send_url_to_web_scraping_lambda("https://example.com", lamba_url)


@patch('requests.post')
def test_send_claims_to_rag_lambda_simple_response(mock_post):
    """Tests function will correctly handle lambda response."""

    lambda_url = "https://my-lambda.aws"

    mock_return = [[
        {"fact": "fact 1", "metadata_1": "..."},
        {"fact": "fact 2", "metadata_1": "..."},
        {"fact": "fact 3", "metadata_1": "..."}
    ]
    ]

    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = mock_return

    mock_claims = [Claim(claim_text="claim 1"), Claim(claim_text="claim 2")]

    result = send_claims_to_rag_lambda(mock_claims, lambda_url)

    assert result == [[{"fact": "fact 1", "metadata_1": "..."},
                      {"fact": "fact 2", "metadata_1": "..."},
                      {"fact": "fact 3", "metadata_1": "..."}]
                      ]


@patch('requests.post')
def test_send_claims_to_rag_lambda_bad_request(mock_post):
    """Tests that a 400 error from the lambda raises a RuntimeError."""

    lamba_url = "https://my-lambda.aws"

    mock_return = {"message": "Invalid claims format", "statusCode": 400}

    mock_response = mock_post.return_value
    mock_response.status_code = 400
    mock_response.json.return_value = mock_return

    mock_claims = [Claim(claim_text="claim 1")]

    with pytest.raises(RuntimeError):
        send_claims_to_rag_lambda(mock_claims, lamba_url)


@patch('requests.post')
def test_send_claims_to_wiki_lambda_simple_response(mock_post):
    """Tests function will correctly handle the Wikipedia lambda response structure."""

    lamba_url = "https://my-wiki-lambda.aws"

    # 1. This matches the specific structure send_claims_to_wiki_lambda expects
    mock_return = {
        "wiki_context": ["evidence 1", "evidence 2", "evidence 3"]
    }

    # 2. Configure the mock response object
    mock_response = mock_post.return_value
    mock_response.status_code = 200  # Sets the HTTP network status
    mock_response.json.return_value = mock_return  # Sets the JSON body

    mock_claims = [Claim(claim_text="claim 1"), Claim(claim_text="claim 2")]

    result = send_claims_to_wiki_lambda(mock_claims, lamba_url)

    assert result == ["evidence 1", "evidence 2", "evidence 3"]


@patch('requests.post')
def test_send_claims_to_wiki_lambda_bad_request(mock_post):
    """Tests that a 400 error from the Wiki lambda raises a RuntimeError."""

    lamba_url = "https://my-wiki-lambda.aws"

    mock_return = {
        "message": "Wikipedia API timeout",
        "statusCode": 400
    }

    mock_response = mock_post.return_value
    mock_response.status_code = 400
    mock_response.json.return_value = mock_return

    mock_claims = [Claim(claim_text="claim 1")]

    with pytest.raises(RuntimeError):
        send_claims_to_wiki_lambda(mock_claims, lamba_url)


def test_create_llm_prompt():
    """Tests that the create_llm_prompt function correctly creates a prompt for the LLM given a list of Claim objects."""

    claims_list = [Claim(claim_text="The sky is blue."),
                   Claim(claim_text="The grass is green.")]

    wiki_list = [{"relevant_sections": "evidence 1", "url": "https://example.com/evidence1"},
                 {"relevant_sections": "evidence 2", "url": "https://example.com/evidence2"}]

    rag_list = [
        [{"content": "fact 1", "created_at": "2024-01-01",
            "source_url": "https://example.com/fact1", "published_at": "2024-01-01"}],
        [{"content": "fact 2", "created_at": "2024-01-02",
            "source_url": "https://example.com/fact2", "published_at": "2024-01-02"}]
    ]

    prompt = create_llm_prompt(claims_list, wiki_list, rag_list)

    context = """Claims:
                [The sky is blue.]
[The grass is green.]
                
                Wikipedia Evidence:
                [evidence 1] (Source: https://example.com/evidence1)
[evidence 2] (Source: https://example.com/evidence2)
                
                RAG Facts:
                [fact 1] (Source: https://example.com/fact1, Date: 2024-01-01)[fact 2] (Source: https://example.com/fact2, Date: 2024-01-02)"""

    assert context in prompt


def test_validate_inputs_for_prompt():
    """Tests that the validate_inputs_for_prompt function raises a ValueError when given invalid inputs."""

    with pytest.raises(ValueError):
        validate_inputs_for_prompt("not a list", ["evidence 1"], [
                                   {"content": "fact 1"}])

    with pytest.raises(ValueError):
        validate_inputs_for_prompt([Claim(claim_text="claim 1")], "not a list", [
                                   {"content": "fact 1"}])

    with pytest.raises(ValueError):
        validate_inputs_for_prompt([Claim(claim_text="claim 1")], [
                                   "evidence 1"], "not a list")
