# pylint: skip-file
import pytest
from chunking import chunk_text


def test_chunking_creates_multiple_chunks():
    text = "This is a test. " * 1000
    chunks = chunk_text(text)

    assert len(chunks) > 1


def test_chunking_handles_empty_input():
    with pytest.raises(ValueError):
        chunks = chunk_text("")


def test_chunking_handles_whitespace_input():
    with pytest.raises(ValueError):
        chunks = chunk_text("   ")


def test_chunking_creates_chunks_of_correct_size():
    text = "A" * 10
    chunk_size = 3
    overlap = 1
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    for chunk in chunks[:-1]:  # all but last chunk should be full size
        assert len(chunk.split(" ")) == chunk_size

    # last chunk should be <= chunk size
    assert len(chunks[-1].split(" ")) <= chunk_size


def test_chunking_creates_correct_chunks():
    text = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
    chunk_size = 5
    overlap = 2
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    expected_chunks = ["A B C D E", "D E F G H", "G H I J K", "J K L M N",
                       "M N O P Q", "P Q R S T", "S T U V W", "V W X Y Z"]
    print(chunks)
    assert chunks == expected_chunks


def test_chunk_overlap():
    text = "A " * 4000
    chunks = chunk_text(text, chunk_size=2000, overlap=500)

    assert len(chunks) >= 2
    # check overlap exists
    assert chunks[0].split(" ")[-500:] == chunks[1].split(" ")[:500]
