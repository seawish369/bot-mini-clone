import pytest

from kb.chunker import CHUNKING_STRATEGY, MAX_CHARS, split_into_chunks

URL = "https://support.optisigns.com/hc/en-us/articles/1-x"
HEADER = f"# Title\n\nArticle URL: {URL}\n\n"


def test_short_article_is_one_chunk_with_the_citation_header():
    chunks = split_into_chunks("Title", URL, "Intro.\n\n## Step\n\nDo it.\n")

    assert chunks == [HEADER + "Intro.\n\n## Step\n\nDo it.\n"]


def test_empty_body_still_gives_one_citable_chunk():
    assert split_into_chunks("Title", URL, "") == [HEADER.rstrip() + "\n"]


def test_long_article_splits_at_headings_and_every_chunk_is_citable():
    body = "\n\n".join(f"## Section {i}\n\n" + ("word " * 120).strip() for i in range(8))

    chunks = split_into_chunks("Title", URL, body, max_chars=1500)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.startswith(HEADER)
        assert len(chunk) <= 1500
        assert chunk[len(HEADER):].startswith("## Section")
    assert sum(chunk.count("## Section") for chunk in chunks) == 8


def test_small_sections_are_packed_together():
    body = "\n\n".join(f"## S{i}\n\nShort." for i in range(5))

    assert len(split_into_chunks("Title", URL, body)) == 1


def test_a_comment_inside_code_is_not_taken_for_a_heading():
    body = "## Request\n\n```bash\ncurl x\n\n## not a heading\n```\n\nDone."

    chunks = split_into_chunks("Title", URL, body, max_chars=400)

    assert len(chunks) == 1
    assert "```bash\ncurl x\n\n## not a heading\n```" in chunks[0]


def test_an_oversized_list_is_split_between_items():
    items = [f"- Item {i}: " + "detail " * 10 for i in range(40)]

    chunks = split_into_chunks("Title", URL, "\n".join(items), max_chars=1000)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1000
        assert all(line.startswith("- Item") for line in chunk[len(HEADER):].splitlines())


def test_an_oversized_line_is_split_at_spaces():
    chunks = split_into_chunks("Title", URL, "x " * 3000, max_chars=1000)

    assert len(chunks) > 3
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_nothing_is_lost_when_splitting():
    body = "\n\n".join(f"## S{i}\n\n" + f"word{i} " * 80 for i in range(30))

    chunks = split_into_chunks("Title", URL, body, max_chars=1200)

    text = " ".join(chunk[len(HEADER):] for chunk in chunks)
    assert all(f"## S{i}" in text and f"word{i}" in text for i in range(30))
    assert max(len(chunk) for chunk in chunks) <= 1200


def test_a_too_small_limit_is_rejected():
    with pytest.raises(ValueError):
        split_into_chunks("Title", URL, "Body", max_chars=100)


def test_store_chunks_are_larger_than_ours_so_one_file_is_one_chunk():
    static = CHUNKING_STRATEGY["static"]

    assert static["chunk_overlap_tokens"] == 0
    assert MAX_CHARS <= static["max_chunk_size_tokens"] <= 4096
