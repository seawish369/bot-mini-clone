import pytest

import ask
from kb.sync import find_or_create_store
from tests.fake_openai import FakeOpenAI


@pytest.fixture
def client(monkeypatch):
    client = FakeOpenAI()
    monkeypatch.setattr(ask, "OpenAI", lambda api_key: client)
    monkeypatch.setattr(ask.Settings, "from_env", classmethod(lambda cls: cls(api_key="sk-test", vector_store_name="test-store")))
    return client


def test_system_prompt_is_the_brief_verbatim():
    assert ask.SYSTEM_PROMPT == (
        "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
        "• Tone: helpful, factual, concise.\n"
        "• Only answer using the uploaded docs.\n"
        "• Max 5 bullet points; else link to the doc.\n"
        '• Cite up to 3 "Article URL:" lines per reply.\n'
    )


def test_question_is_answered_with_file_search_on_our_store(client, capsys):
    store_id = find_or_create_store(client, "test-store")

    assert ask.main(["How", "do", "I", "add", "a", "YouTube", "video?"]) == 0

    call = client.responses.calls[0]
    assert call["instructions"] == ask.SYSTEM_PROMPT
    assert call["input"] == "How do I add a YouTube video?"
    assert call["tools"] == [{"type": "file_search", "vector_store_ids": [store_id], "max_num_results": 5}]
    assert "Article URL:" in capsys.readouterr().out


def test_default_question_is_the_sample_from_the_brief(client):
    find_or_create_store(client, "test-store")

    ask.main([])

    assert client.responses.calls[0]["input"] == ask.DEFAULT_QUESTION


def test_missing_store_exits_one_without_creating_it(client):
    assert ask.main(["anything"]) == 1
    assert client.stores == {}
