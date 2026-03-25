# pylint: skip-file
from main import is_valid_event


class TestIsValidEvent:
    def test_valid_event(self):
        event = {
            "queries": ["What is RAG?", "How does it work?"]
        }
        assert is_valid_event(event) == True

    def test_missing_queries_key(self):
        event = {
            "not_queries": ["What is RAG?"]
        }
        assert is_valid_event(event) == False

    def test_queries_not_a_list(self):
        event = {
            "queries": "What is RAG?"
        }
        assert is_valid_event(event) == False

    def test_query_in_queries_not_a_string(self):
        event = {
            "queries": ["What is RAG?", 123]
        }
        assert is_valid_event(event) == False

    def test_event_not_a_dict(self):
        event = "This is not a dict"
        assert is_valid_event(event) == False
