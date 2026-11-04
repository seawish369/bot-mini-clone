import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from kb.config import LOG_LEVEL, OUTPUT_DIR, Settings
from kb.document import Document, build_document
from kb.scraper import fetch_articles

log = logging.getLogger("bot")


def write_markdown(docs: list[Document], output_dir: Path, remove_stale: bool) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (output_dir / doc.filename).write_text(doc.markdown, encoding="utf-8")

    removed = 0
    if remove_stale:
        current = {doc.filename for doc in docs}
        for path in output_dir.glob("*.md"):
            if path.name not in current:
                path.unlink()
                removed += 1
    return removed


def run(settings: Settings, limit: int, scrape_only: bool) -> dict:
    started = time.monotonic()
    summary: dict = {"started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    articles = fetch_articles(limit=limit)
    docs = [build_document(article) for article in articles]
    removed_files = write_markdown(docs, OUTPUT_DIR, remove_stale=limit == 0)
    summary["articles_scraped"] = len(docs)
    summary["markdown_files_written"] = len(docs)
    summary["markdown_files_removed"] = removed_files
    log.info("scraped %d articles, wrote %d Markdown files to %s/", len(docs), len(docs), OUTPUT_DIR)

    if scrape_only:
        log.info("--scrape-only: skipping the vector store upload")
    else:
        raise SystemExit("vector store upload is not implemented yet; run with --scrape-only")

    summary["duration_s"] = round(time.monotonic() - started, 1)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape the help center to Markdown and sync it to a vector store.")
    parser.add_argument("--limit", type=int, default=0, help="only the first N articles (0 = all)")
    parser.add_argument("--scrape-only", action="store_true", help="write Markdown without uploading")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    settings = Settings.from_env()
    try:
        summary = run(settings, limit=args.limit, scrape_only=args.scrape_only)
    except SystemExit as stop:
        log.error("%s", stop)
        return 1
    except Exception:
        log.exception("run failed")
        return 1

    summary["status"] = "ok"
    (OUTPUT_DIR / "last_run.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log.info("summary %s", json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
