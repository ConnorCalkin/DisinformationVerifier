import os
from dotenv import load_dotenv
from streamlit_functions import (get_claims_from_text, query_LLM,
                                 convert_claims_string_to_list, Claim)


from openai import OpenAI

load_dotenv()


def test_query_LLM_basic_claims():
    """Tests that the query_LLM function correctly extracts claims from a simple input text."""

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = "The sky is blue. The grass is green. Water is wet."

    assert query_LLM(
        prompt, client) == "|The sky is blue.\n|The grass is green.\n|Water is wet."


def test_query_LLM_no_claims():
    """Tests that the query_LLM function returns an empty
    string when no claims are present in the input text."""

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = "I love the sky. The grass is nice. Water is refreshing."

    assert query_LLM(prompt, client) == ""


def test_convert_claims_string_to_list():
    """Tests that the convert_claims_string_to_list function
    correctly converts a claims string into a list of Claim objects."""

    claims_string = "|The sky is blue.\n|The grass is green.\n|Water is wet."

    claims_list = convert_claims_string_to_list(claims_string)

    assert len(claims_list) == 3
    assert claims_list[0].claim_text == "The sky is blue."
    assert claims_list[1].claim_text == "The grass is green."
    assert claims_list[2].claim_text == "Water is wet."


def test_get_claims_from_text():
    """Tests that the get_claims_from_text function correctly extracts claims
    from a simple input text and returns a list of Claim objects."""

    text_input = "The sky is blue. The grass is green. Water is wet."

    claims_list = get_claims_from_text(text_input)

    assert len(claims_list) == 3

    assert isinstance(claims_list[0], Claim)
    assert isinstance(claims_list[1], Claim)
    assert isinstance(claims_list[2], Claim)

    assert claims_list[0].claim_text == "The sky is blue."
    assert claims_list[1].claim_text == "The grass is green."
    assert claims_list[2].claim_text == "Water is wet."
