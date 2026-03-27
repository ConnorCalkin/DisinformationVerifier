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
                                 convert_llm_response_to_dict, validate_response_format,
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

    mock_response = mock_post.return_value

    mock_response.json.return_value = {
        "message": "mock_text", "status_code": 200}

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
                [evidence 1] (Source: https://example.com/evidence1)
[evidence 2] (Source: https://example.com/evidence2)
                
                RAG Facts:
                [fact 1] (Source: https://example.com/fact1, Date: 2024-01-01)[fact 2] (Source: https://example.com/fact2, Date: 2024-01-02)

                ### Instructions:
1. Assign one rating: SUPPORTED, CONTRADICTED, MISLEADING, or UNSURE.
2. A claim is MISLEADING if it is directionally correct but lacks the specific detail, nuance, or precision found in the sources.
3. Provide a brief 1-2 sentence explanation.
4. Identify if the information came from "Wikipedia", a URL, or multiple.
5. DO NOT include any sources if the claim is rated UNSURE.
6. DO INCLUDE " ' " characters in the response to allow for clear parsing of the explanation and sources.

### Output Format:
|'claim_made','rating','[Explanation]'. 'Sources: [Wikipedia and/or the specific Source URL(s) or 'None' if UNSURE]' """


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


def test_convert_llm_response_to_dict_1():

    llm_response = """
|'The sky is a really light blue.','SUPPORTED','The sources indicate the sky appears blue due to atmospheric scattering and is described as blue during the day.', 'Sources: Wiki, https://example.com/sky'\n
|'The grass is green.','UNSURE','No evidence in the provided Wiki or RAG facts about grass color.', 'Sources: None'
"""

    result = convert_llm_response_to_dict(llm_response)

    assert result == [
        {
            "claim": "The sky is a really light blue.",
            "rating": "SUPPORTED",
            "explanation": "The sources indicate the sky appears blue due to atmospheric scattering and is described as blue during the day."
            " Sources: Wiki, https://example.com/sky",
        },
        {
            "claim": "The grass is green.",
            "rating": "UNSURE",
            "explanation": "No evidence in the provided Wiki or RAG facts about grass color. Sources: None"
        }
    ]


def test_convert_llm_response_to_dict_2():

    llm_response = """
|'Donald trump is 30','CONTRADICTED','The provided Wikipedia article states Donald Trump was born in 1946 and was the oldest president at 78 during his second term, not 30.', 'Sources: Wiki'
"""

    result = convert_llm_response_to_dict(llm_response)

    assert result == [
        {
            "claim": "Donald trump is 30",
            "rating": "CONTRADICTED",
            "explanation": "The provided Wikipedia article states Donald Trump was born in 1946 and was the oldest president at 78 during his second term, not 30. Sources: Wiki"
        }]


def test_validate_response_format_correct_format_multiple_claims():
    """Tests that the validate_response_format function does not raise an error when given a correctly formatted response."""

    llm_response = """|'The sky is a really light blue.',
'SUPPORTED','Wiki cites the sky appears blue due to 
scattering and the RAG fact describes it as blue during the day, 
aligning with the claim.' Sources: Wiki, https://example.com/sky
|'The grass is green.','UNSURE','No grass-color information is 
provided in the Wiki or RAG facts.' Sources: None
"""

    try:
        validate_response_format(llm_response)
    except ValueError:
        pytest.fail("validate_response_format raised ValueError unexpectedly!")


def test_validate_response_format_correct_format_single_claims():
    """Tests that the validate_response_format function does not raise an error when given a correctly formatted response."""

    llm_response = """|'The sky is a really light blue.',
'SUPPORTED','Wiki cites the sky appears blue due 
to scattering and the RAG fact describes it as blue during the day, 
aligning with the claim.' Sources: Wiki, https://example.com/sky
"""

    try:
        validate_response_format(llm_response)
    except ValueError:
        pytest.fail("validate_response_format raised ValueError unexpectedly!")


def test_validate_response_format_incorrect_format():
    """Tests that the validate_response_format function 
    raises a ValueError when given an incorrectly formatted response."""

    llm_response = """The sky is a really light blue.
    SUPPORTED Wiki cites the sky appears blue due to
    scattering and the RAG fact describes it as blue during 
    the day, aligning with the claim. Sources: Wiki, https://example.com/sky"""

    with pytest.raises(ValueError):
        validate_response_format(llm_response)

    llm_response = """|'The sky is a really light blue.',
'supported', Wiki cites the sky appears blue due to
scattering and the RAG fact describes it as blue during 
the day, aligning with the claim. Sources: Wiki, https://example.com/sky"""

    with pytest.raises(ValueError):
        validate_response_format(llm_response)
