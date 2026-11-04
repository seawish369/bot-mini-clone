from dataclasses import replace
from types import SimpleNamespace

import pytest

from kb.chunker import CHUNKING_STRATEGY
from kb.document import build_document
from kb.sync import RemoteArticle, apply_plan, find_or_create_store, load_remote_state, plan_sync
from tests.fake_openai import FakeOpenAI


@pytest.fixture
def docs(articles):
    return [build_document(article) for article in articles]


@pytest.fixture
def client():
    return FakeOpenAI()


def sync_once(client, docs, complete_scrape=True):
    store_id = find_or_create_store(client, "test-store")
    plan = plan_sync(docs, load_remote_state(client, store_id), complete_scrape)
    return apply_plan(client, store_id, plan)


def files_of(client, doc):
    return {f for f, item in client.items.items() if item.attributes["article_id"] == str(doc.article_id)}


def remote(doc, content_hash=None, healthy=True):
    return RemoteArticle(doc.article_id, content_hash or doc.content_hash, ["file-1"], 1, healthy)


def test_plan_adds_updates_skips_and_removes(docs):
    new, changed = docs
    gone = RemoteArticle(999, "old", ["file-9"], 1)
    state = {changed.article_id: remote(changed, content_hash="old"), 999: gone}

    plan = plan_sync(docs, state, complete_scrape=True)

    assert plan.added == [new]
    assert [doc for doc, _ in plan.updated] == [changed]
    assert plan.skipped == []
    assert plan.removed == [gone]


def test_plan_skips_unchanged_articles(docs):
    plan = plan_sync(docs, {doc.article_id: remote(doc) for doc in docs}, complete_scrape=True)

    assert plan.skipped == docs
    assert not plan.added and not plan.updated and not plan.removed


def test_plan_reuploads_unhealthy_articles(docs):
    state = {doc.article_id: remote(doc, healthy=False) for doc in docs}

    plan = plan_sync(docs, state, complete_scrape=True)

    assert [doc for doc, _ in plan.updated] == docs


def test_partial_scrape_never_removes(docs):
    state = {999: RemoteArticle(999, "old", ["file-9"], 1)}

    assert plan_sync(docs[:1], state, complete_scrape=False).removed == []


def test_store_is_created_once_with_our_chunking_strategy(client):
    first = find_or_create_store(client, "test-store")

    assert find_or_create_store(client, "test-store") == first
    assert client.stores[first].chunking_strategy == CHUNKING_STRATEGY
    assert len(client.stores) == 1


def test_remote_state_groups_chunks_and_flags_broken_articles(client):
    def item(file_id, article_id, content_hash, part, parts, status="completed"):
        attributes = {"article_id": str(article_id), "content_hash": content_hash, "part": part, "parts": parts}
        client.items[file_id] = SimpleNamespace(id=file_id, status=status, attributes=attributes)

    item("f1", 1, "h", 1, 2)
    item("f2", 1, "h", 2, 2)
    item("f3", 2, "h", 1, 2)
    item("f4", 3, "h", 1, 1, status="failed")
    item("f5", 4, "old", 1, 1)
    item("f6", 4, "new", 1, 1)
    client.items["f7"] = SimpleNamespace(id="f7", status="completed", attributes=None)

    state = load_remote_state(client, "vs-1")

    assert sorted(state) == [1, 2, 3, 4]
    assert state[1].file_ids == ["f1", "f2"] and state[1].healthy
    assert not state[2].healthy
    assert not state[3].healthy
    assert not state[4].healthy


def test_first_run_adds_and_second_run_skips(client, docs):
    first = sync_once(client, docs)

    assert (first.added, first.updated, first.skipped, first.failed) == (2, 0, 0, 0)
    assert first.files_uploaded == first.chunks_embedded == len(client.items)

    second = sync_once(client, docs)

    assert (second.added, second.updated, second.skipped, second.files_uploaded) == (0, 0, 2, 0)


def test_every_uploaded_chunk_carries_attributes_and_citation(client, docs):
    sync_once(client, docs)

    for file_id, item in client.items.items():
        name, text = client.uploaded[file_id]
        attributes = item.attributes
        assert name.endswith(f"--{attributes['part']:02d}.md")
        assert f"Article URL: {attributes['url']}" in text
        assert set(attributes) == {"article_id", "content_hash", "part", "parts", "url", "title"}


def test_changed_article_is_reuploaded_and_old_chunks_removed(client, docs):
    sync_once(client, docs)
    old_files = files_of(client, docs[0])
    changed = replace(docs[0], body=docs[0].body + "\nNew paragraph.\n")

    stats = sync_once(client, [changed, docs[1]])

    assert (stats.added, stats.updated, stats.skipped) == (0, 1, 1)
    assert {client.items[f].attributes["content_hash"] for f in files_of(client, changed)} == {changed.content_hash}
    assert old_files.isdisjoint(client.items)
    assert old_files.isdisjoint(client.uploaded)


def test_removed_article_is_deleted_only_on_a_complete_scrape(client, docs):
    sync_once(client, docs)

    assert sync_once(client, docs[:1], complete_scrape=False).removed == 0
    assert sync_once(client, docs[:1], complete_scrape=True).removed == 1
    assert {item.attributes["article_id"] for item in client.items.values()} == {str(docs[0].article_id)}


def test_failed_chunk_is_counted_and_healed_on_the_next_run(client, docs):
    client.fail_parts = {1}

    first = sync_once(client, docs)

    assert first.failed == 2 and first.added == 0

    client.fail_parts = set()
    second = sync_once(client, docs)

    assert (second.updated, second.failed) == (2, 0)
    assert all(item.status == "completed" for item in client.items.values())
    assert sync_once(client, docs).skipped == 2
