import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from openai import OpenAI

from kb.chunker import CHUNKING_STRATEGY, split_into_chunks
from kb.document import Document

log = logging.getLogger(__name__)

UPLOAD_WORKERS = 8
PAGE_SIZE = 100


@dataclass
class RemoteArticle:
    article_id: int
    content_hash: str
    file_ids: list[str] = field(default_factory=list)
    parts: int = 0
    healthy: bool = True


@dataclass
class SyncPlan:
    added: list[Document] = field(default_factory=list)
    updated: list[tuple[Document, RemoteArticle]] = field(default_factory=list)
    skipped: list[Document] = field(default_factory=list)
    removed: list[RemoteArticle] = field(default_factory=list)


@dataclass
class SyncStats:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    removed: int = 0
    files_uploaded: int = 0
    chunks_embedded: int = 0
    failed: int = 0


@dataclass(frozen=True)
class ChunkJob:
    doc: Document
    part: int
    parts: int
    text: str


def plan_sync(local: list[Document], remote: dict[int, RemoteArticle], complete_scrape: bool) -> SyncPlan:
    plan = SyncPlan()
    for doc in local:
        existing = remote.get(doc.article_id)
        if existing is None:
            plan.added.append(doc)
        elif existing.content_hash != doc.content_hash or not existing.healthy:
            plan.updated.append((doc, existing))
        else:
            plan.skipped.append(doc)

    if complete_scrape:
        scraped = {doc.article_id for doc in local}
        plan.removed = [article for article_id, article in remote.items() if article_id not in scraped]
    return plan


def find_store(client: OpenAI, name: str) -> str | None:
    for store in client.vector_stores.list(limit=PAGE_SIZE):
        if store.name == name:
            return store.id
    return None


def find_or_create_store(client: OpenAI, name: str) -> str:
    store_id = find_store(client, name)
    if store_id:
        return store_id
    store = client.vector_stores.create(name=name, chunking_strategy=CHUNKING_STRATEGY)
    log.info("created vector store %s (%s)", name, store.id)
    return store.id


def load_remote_state(client: OpenAI, store_id: str) -> dict[int, RemoteArticle]:
    remote: dict[int, RemoteArticle] = {}
    for item in client.vector_stores.files.list(vector_store_id=store_id, limit=PAGE_SIZE):
        attributes = item.attributes or {}
        if "article_id" not in attributes:
            continue

        article_id = int(attributes["article_id"])
        content_hash = str(attributes.get("content_hash", ""))
        article = remote.setdefault(article_id, RemoteArticle(article_id, content_hash))
        article.file_ids.append(item.id)
        article.parts = max(article.parts, int(attributes.get("parts") or 0))
        if item.status != "completed" or content_hash != article.content_hash:
            article.healthy = False

    for article in remote.values():
        if len(article.file_ids) != article.parts:
            article.healthy = False
    return remote


def apply_plan(client: OpenAI, store_id: str, plan: SyncPlan) -> SyncStats:
    stats = SyncStats(skipped=len(plan.skipped))
    to_upload = plan.added + [doc for doc, _ in plan.updated]
    jobs = [job for doc in to_upload for job in chunk_jobs(doc)]

    with ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as pool:
        results = list(pool.map(lambda job: upload_chunk(client, store_id, job), jobs))

    ok_by_article: dict[int, list[bool]] = defaultdict(list)
    for job, ok in zip(jobs, results):
        ok_by_article[job.doc.article_id].append(ok)
    stats.files_uploaded = len(results)
    stats.chunks_embedded = sum(results)
    stats.failed = len(results) - stats.chunks_embedded

    for doc in plan.added:
        if all(ok_by_article[doc.article_id]):
            stats.added += 1
    for doc, old in plan.updated:
        if all(ok_by_article[doc.article_id]):
            remove_files(client, store_id, old.file_ids)
            stats.updated += 1
    for old in plan.removed:
        remove_files(client, store_id, old.file_ids)
        stats.removed += 1
    return stats


def chunk_jobs(doc: Document) -> list[ChunkJob]:
    chunks = split_into_chunks(doc.title, doc.url, doc.body)
    return [ChunkJob(doc, part, len(chunks), text) for part, text in enumerate(chunks, 1)]


def upload_chunk(client: OpenAI, store_id: str, job: ChunkJob) -> bool:
    doc = job.doc
    try:
        uploaded = client.files.create(
            file=(f"{doc.slug}--{job.part:02d}.md", job.text.encode("utf-8")),
            purpose="assistants",
        )
        indexed = client.vector_stores.files.create_and_poll(
            file_id=uploaded.id,
            vector_store_id=store_id,
            chunking_strategy=CHUNKING_STRATEGY,
            attributes={
                "article_id": str(doc.article_id),
                "content_hash": doc.content_hash,
                "part": job.part,
                "parts": job.parts,
                "url": doc.url,
                "title": doc.title[:500],
            },
        )
    except Exception:
        log.exception("chunk %d/%d of article %d failed to upload", job.part, job.parts, doc.article_id)
        return False

    if indexed.status != "completed":
        log.error("chunk %d/%d of article %d failed to index: %s", job.part, job.parts, doc.article_id, indexed.last_error)
        return False
    return True


def remove_files(client: OpenAI, store_id: str, file_ids: list[str]) -> None:
    for file_id in file_ids:
        client.vector_stores.files.delete(file_id=file_id, vector_store_id=store_id)
        try:
            client.files.delete(file_id)
        except Exception as error:
            log.debug("could not delete file %s: %s", file_id, error)
