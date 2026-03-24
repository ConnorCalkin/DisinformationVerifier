# pylint: skip-file
from ingest import is_valid_article_text, build_metadata


def test_is_valid_article_text():
    assert is_valid_article_text("This is a valid article text.") == True
    assert is_valid_article_text("   ") == False
    assert is_valid_article_text("") == False
    assert is_valid_article_text("   Valid text with spaces   ") == True

# TODO: Add tests for build_metadata when we have a
# better idea of what metadata we want to include
