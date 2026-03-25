"""Test suite for streamlit_functions.py. 
"""

# import os
# from dotenv import load_dotenv
import pytest
# from streamlit_functions import (get_claims_from_text, query_llm,
#                                  convert_claims_string_to_list, Claim)

from streamlit_functions import convert_claims_string_to_list, Claim


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
