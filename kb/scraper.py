import logging
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from kb.config import HELP_CENTER_URL, LOCALE

log = logging.getLogger(__name__)

PAGE_SIZE = 100
TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Article:
    id: int
    title: str
    html_url: str
    updated_at: str
    body: str


def make_session() -> requests.Session:
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "bot-mini-clone/1.0 (help-center sync)"
    return session


def parse_article(raw: dict) -> Article:
    return Article(
        id=int(raw["id"]),
        title=(raw.get("title") or raw.get("name") or "").strip(),
        html_url=raw["html_url"],
        updated_at=raw.get("updated_at") or raw.get("edited_at") or "",
        body=raw.get("body") or "",
    )


def fetch_articles(
    base_url: str = HELP_CENTER_URL,
    locale: str = LOCALE,
    limit: int = 0,
    session: requests.Session | None = None,
) -> list[Article]:
    session = session or make_session()
    url: str | None = f"{base_url}/api/v2/help_center/{locale}/articles.json?per_page={PAGE_SIZE}"
    articles: list[Article] = []

    while url:
        response = session.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()

        for raw in payload.get("articles", []):
            if raw.get("draft"):
                continue
            articles.append(parse_article(raw))
            if limit and len(articles) >= limit:
                return articles

        url = payload.get("next_page")
        log.debug("fetched page, %d articles so far", len(articles))

    return articles
