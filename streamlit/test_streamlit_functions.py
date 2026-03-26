"""Test suite for streamlit_functions.py. 
"""

# import os
# from dotenv import load_dotenv
import pytest
from unittest.mock import patch, MagicMock
# from streamlit_functions import (get_claims_from_text, query_llm,
#                                  convert_claims_string_to_list, Claim)

from streamlit_functions import (convert_claims_string_to_list, send_url_to_web_scraping_lambda,
                                 send_claims_to_rag_lambda, send_claims_to_wiki_lambda,
                                 create_llm_prompt, validate_inputs_for_prompt,
                                 Claim)


# from openai import OpenAI

# load_dotenv()


# def test_query_llm_basic_claims():
#     """Tests that the query_llm function correctly extracts claims from a simple input text."""

#     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

#     prompt = "The sky is blue. The grass is green. Water is wet."

#     assert query_llm(
#         prompt, client) == "|The sky is blue.\n|The grass is green.\n|Water is wet."


# def test_query_llm_no_claims():
#     """Tests that the query_llm function returns an empty
#     string when no claims are present in the input text."""

#     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

#     prompt = "I love the sky. The grass is nice. Water is refreshing."

#     assert query_llm(prompt, client) == ""


def test_convert_claims_string_to_list():
    """Tests that the convert_claims_string_to_list function
    correctly converts a claims string into a list of Claim objects."""

    claims_string = "|The sky is blue.\n|The grass is green.\n|Water is wet."

    claims_list = convert_claims_string_to_list(claims_string)

    assert len(claims_list) == 3
    assert claims_list[0].claim_text == "The sky is blue."
    assert claims_list[1].claim_text == "The grass is green."
    assert claims_list[2].claim_text == "Water is wet."


# def test_get_claims_from_text():
#     """Tests that the get_claims_from_text function correctly extracts claims
#     from a simple input text and returns a list of Claim objects."""

#     text_input = "The sky is blue. The grass is green. Water is wet."

#     claims_list = get_claims_from_text(text_input)

#     assert len(claims_list) == 3

#     assert isinstance(claims_list[0], Claim)
#     assert isinstance(claims_list[1], Claim)
#     assert isinstance(claims_list[2], Claim)

#     assert claims_list[0].claim_text == "The sky is blue."
#     assert claims_list[1].claim_text == "The grass is green."
#     assert claims_list[2].claim_text == "Water is wet."

def test_convert_claims_string_to_list_empty_string():
    """Tests that the convert_claims_string_to_list function returns an empty list when given an empty string."""

    claims_string = ""

    with pytest.raises(ValueError):
        convert_claims_string_to_list(claims_string)

def test_comvert_claims_string_to_list_malformed_string_1():
    """Tests that the convert_claims_string_to_list function raises a ValueError when given a malformed claims string."""

    claims_string = "The sky is blue.\nThe grass is green.\nWater is wet."

    assert [
        claim.claim_text for claim in convert_claims_string_to_list(claims_string) 
    ] == ["The sky is blue.", "The grass is green.", "Water is wet."]


def test_comvert_claims_string_to_list_malformed_string_2():
    """Tests that the convert_claims_string_to_list function raises a ValueError when given a malformed claims string."""

    claims_string = "The sky is blue.  |The grass is green.\n| Water is wet."

    assert [
        claim.claim_text for claim in convert_claims_string_to_list(claims_string)
    ] == ["The sky is blue.", "The grass is green.", "Water is wet."]

def test_comvert_claims_string_to_list_malformed_string_3():
    """Tests that the convert_claims_string_to_list function raises a ValueError when given a malformed claims string."""

    claims_string = "The sky is blue.  The grass is green. Water is wet."

    with pytest.raises(ValueError):
        convert_claims_string_to_list(claims_string)





@patch('requests.post')
def test_lambda_logic_simple_response(mock_post):

    lamba_url = "https://my-lambda.aws"

    mock_return = {"message": "mock_text", "status_code": 200}
    
    mock_post.return_value.json.return_value = mock_return

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

    lamba_url = "https://my-lambda.aws"

    mock_return = {
        "statusCode": 200,
        "body": [{"fact":"fact 1","metadata_1":"..."},
                 {"fact":"fact 2","metadata_1":"..."},
                 {"fact":"fact 3","metadata_1":"..."}]
    }

    mock_post.return_value.json.return_value = mock_return
    mock_claims = [Claim(claim_text="claim 1"), Claim(claim_text="claim 2")]

    result = send_claims_to_rag_lambda(mock_claims, lamba_url)

    assert result == [{"fact": "fact 1", "metadata_1": "..."},
                      {"fact": "fact 2", "metadata_1": "..."},
                      {"fact": "fact 3", "metadata_1": "..."}]


@patch('requests.post')
def test_send_claims_to_rag_lambda_bad_request(mock_post):

    lamba_url = "https://my-lambda.aws"

    mock_return = {"message": "error_message", "status_code": 400}

    mock_post.return_value.json.return_value = mock_return

    with pytest.raises(RuntimeError):
       send_claims_to_rag_lambda("https://example.com", lamba_url)


@patch('requests.post')
def test_send_claims_to_wiki_lambda_simple_response(mock_post):
    """Tests function will correctly handle lambda response."""

    lamba_url = "https://my-lambda.aws"

    mock_return = {
        "statusCode": 200,
        "body": {"wiki_context":["evidence 1", "evidence 2", "evidence 3"]}
    }

    mock_post.return_value.json.return_value = mock_return
    mock_claims = [Claim(claim_text="claim 1"), Claim(claim_text="claim 2")]

    result = send_claims_to_wiki_lambda(mock_claims, lamba_url)

    assert result == ["evidence 1", "evidence 2", "evidence 3"]
    

@patch('requests.post')
def test_send_claims_to_wiki_lambda_bad_request(mock_post):

    lamba_url = "https://my-lambda.aws"

    mock_return = {"message": "error_message", "status_code": 400}

    mock_post.return_value.json.return_value = mock_return

    with pytest.raises(RuntimeError):
       send_claims_to_wiki_lambda("https://example.com", lamba_url)


def test_create_llm_prompt():
    """Tests that the create_llm_prompt function correctly creates a prompt for the LLM given a list of Claim objects."""

    claims_list = [Claim(claim_text="The sky is blue."), Claim(claim_text="The grass is green.")]

    wiki_list = ["evidence 1", "evidence 2"]

    rag_list = [
        {"content": "fact 1", "created_at": "2024-01-01", "source_url": "https://example.com/fact1"},
        {"content": "fact 2", "created_at": "2024-01-02", "source_url": "https://example.com/fact2"}
    ]

    prompt = create_llm_prompt(claims_list, wiki_list, rag_list)

    assert prompt == """Evaluate the following claims based on
                the provided Wikipedia evidence and RAG facts. 
                For each claim, assign a rating of 
                SUPPORTED, CONTRADICTED, MISLEADING, or UNSURE
                based strictly on the provided evidence. 
                Provide a brief explanation for each rating and, as a final entry, 
                include all the sources of the evidence used, date and title if available.

                Claims:
                [The sky is blue.]
[The grass is green.]
                
                Wikipedia Evidence:
                [evidence 1]
[evidence 2]
                
                RAG Facts:
                [fact 1] (Source: https://example.com/fact1, Date: 2024-01-01)
[fact 2] (Source: https://example.com/fact2, Date: 2024-01-02)
                
                ### Instructions:
1. Assign one rating: SUPPORTED, CONTRADICTED, MISLEADING, or UNSURE.
2. A claim is MISLEADING if it is directionally correct but lacks the specific detail, nuance, or precision found in the sources.
3. Provide a brief 1-2 sentence explanation.
4. Identify if the information came from "Wiki", "URL", or "Both".

### Output Format:
Return ONLY the results. Each claim must be on a new line starting with a pipe character:
|'claim_made','rating','[Explanation sentence]. Sources: [Source Type]'"""
    
def test_validate_inputs_for_prompt():
    """Tests that the validate_inputs_for_prompt function raises a ValueError when given invalid inputs."""

    with pytest.raises(ValueError):
        validate_inputs_for_prompt("not a list", ["evidence 1"], [{"content": "fact 1"}])

    with pytest.raises(ValueError):
        validate_inputs_for_prompt([Claim(claim_text="claim 1")], "not a list", [{"content": "fact 1"}])

    with pytest.raises(ValueError):
        validate_inputs_for_prompt([Claim(claim_text="claim 1")], ["evidence 1"], "not a list")