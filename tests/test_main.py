import json

import pytest

import main
from tests.fake_openai import FakeOpenAI


@pytest.fixture
def output_dir(tmp_path, monkeypatch, articles):
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(main, "fetch_articles", lambda limit=0: articles[:limit] if limit else articles)
    return tmp_path


def test_scrape_only_writes_markdown_and_summary(output_dir):
    assert main.main(["--scrape-only"]) == 0

    files = sorted(path.name for path in output_dir.glob("*.md"))
    assert files == ["360000002222-using-the-optisigns-api.md", "360051234567-how-to-add-a-youtube-video.md"]

    summary = json.loads((output_dir / "last_run.json").read_text())
    assert summary["articles_scraped"] == 2
    assert summary["status"] == "ok"


def test_full_scrape_removes_stale_files(output_dir):
    (output_dir / "999-removed-article.md").write_text("old")

    assert main.main(["--scrape-only"]) == 0

    assert not (output_dir / "999-removed-article.md").exists()


def test_partial_scrape_keeps_other_files(output_dir):
    (output_dir / "999-removed-article.md").write_text("old")

    assert main.main(["--scrape-only", "--limit", "1"]) == 0

    assert (output_dir / "999-removed-article.md").exists()
    assert len(list(output_dir.glob("*.md"))) == 2


@pytest.fixture
def openai(monkeypatch):
    client = FakeOpenAI()
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.setattr(main, "OpenAI", lambda api_key: client)
    return client


def test_full_run_uploads_then_skips_and_exits_zero(output_dir, openai):
    assert main.main([]) == 0
    first = json.loads((output_dir / "last_run.json").read_text())

    assert main.main([]) == 0
    second = json.loads((output_dir / "last_run.json").read_text())

    assert (first["added"], first["skipped"], first["chunks_embedded"]) == (2, 0, len(openai.items))
    assert (second["added"], second["skipped"], second["files_uploaded"]) == (0, 2, 0)
    assert second["status"] == "ok"


def test_failed_chunk_makes_the_run_exit_one(output_dir, openai):
    openai.fail_parts = {1}

    assert main.main([]) == 1

    summary = json.loads((output_dir / "last_run.json").read_text())
    assert summary["status"] == "partial"
    assert summary["failed"] == 2


def test_missing_api_key_exits_one(output_dir, monkeypatch):
    monkeypatch.setattr(main.Settings, "from_env", classmethod(lambda cls: cls(api_key="", vector_store_name="x")))

    assert main.main([]) == 1
