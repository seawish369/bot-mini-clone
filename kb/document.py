import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

from kb.convert import html_to_markdown
from kb.scraper import Article

FORMAT_VERSION = "1"
MAX_SLUG_LENGTH = 100


@dataclass(frozen=True)
class Document:
    article_id: int
    title: str
    url: str
    updated_at: str
    slug: str
    body: str
    markdown: str

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"

    @property
    def content_hash(self) -> str:
        payload = "\n".join((FORMAT_VERSION, self.title, self.url, self.body))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_document(article: Article) -> Document:
    body = html_to_markdown(article.body)
    markdown = (
        "---\n"
        f"title: {json.dumps(article.title, ensure_ascii=False)}\n"
        f"article_id: {article.id}\n"
        f"url: {article.html_url}\n"
        f"updated_at: {article.updated_at}\n"
        "---\n\n"
        f"# {article.title}\n\n"
        f"Article URL: {article.html_url}\n\n"
        f"{body}"
    )
    return Document(
        article_id=article.id,
        title=article.title,
        url=article.html_url,
        updated_at=article.updated_at,
        slug=slug_for(article),
        body=body,
        markdown=markdown,
    )


def slug_for(article: Article) -> str:
    last_segment = article.html_url.rstrip("/").rsplit("/", 1)[-1]
    slug = slugify(last_segment)
    if not slug.startswith(str(article.id)):
        slug = f"{article.id}-{slugify(article.title)}"
    return slug[:MAX_SLUG_LENGTH].rstrip("-")


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
