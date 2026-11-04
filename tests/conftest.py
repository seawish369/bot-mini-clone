import json
from pathlib import Path

import pytest

from kb.scraper import Article, fetch_articles

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self):
        self.urls: list[str] = []

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.urls.append(url)
        name = "page2.json" if "page=2" in url else "page1.json"
        return FakeResponse(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def articles(session: FakeSession) -> list[Article]:
    return fetch_articles(session=session)
