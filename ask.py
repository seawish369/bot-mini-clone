import argparse
import sys
from pathlib import Path

from openai import OpenAI

from kb.config import MODEL, Settings
from kb.sync import find_store

SYSTEM_PROMPT = (Path(__file__).parent / "assistant" / "system_prompt.md").read_text(encoding="utf-8")
DEFAULT_QUESTION = "How do I add a YouTube video?"
MAX_RESULTS = 5


def ask(client: OpenAI, store_id: str, question: str, model: str = MODEL) -> str:
    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=question,
        tools=[{"type": "file_search", "vector_store_ids": [store_id], "max_num_results": MAX_RESULTS}],
    )
    return response.output_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask OptiBot a question, answered from the vector store.")
    parser.add_argument("question", nargs="*", help=f'defaults to "{DEFAULT_QUESTION}"')
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args(argv)
    question = " ".join(args.question) or DEFAULT_QUESTION

    settings = Settings.from_env()
    if not settings.api_key:
        print("API_KEY is not set (see .env.sample)", file=sys.stderr)
        return 1

    client = OpenAI(api_key=settings.api_key)
    store_id = find_store(client, settings.vector_store_name)
    if not store_id:
        print(f"No vector store named {settings.vector_store_name!r}: run `python main.py` first.", file=sys.stderr)
        return 1

    print(f"Q: {question}\n")
    print(ask(client, store_id, question, model=args.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
