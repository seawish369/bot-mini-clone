import re

MAX_CHARS = 2400
MIN_BUDGET = 200

STORE_CHUNK_TOKENS = 1600
STORE_OVERLAP_TOKENS = 0
CHUNKING_STRATEGY = {
    "type": "static",
    "static": {"max_chunk_size_tokens": STORE_CHUNK_TOKENS, "chunk_overlap_tokens": STORE_OVERLAP_TOKENS},
}

HEADING = re.compile(r"^#{2,4} \S")
FENCE = "```"


def split_into_chunks(title: str, url: str, body: str, max_chars: int = MAX_CHARS) -> list[str]:
    header = f"# {title}\n\nArticle URL: {url}\n\n"
    budget = max_chars - len(header) - 1
    if budget < MIN_BUDGET:
        raise ValueError("max_chars is too small for the chunk header")

    chunks: list[str] = []
    current = ""
    for unit in split_units(body, budget):
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= budget:
            current = candidate
        else:
            chunks.append(current)
            current = unit
    if current or not chunks:
        chunks.append(current)

    return [f"{header}{chunk}".rstrip() + "\n" for chunk in chunks]


def split_units(body: str, budget: int) -> list[str]:
    units: list[str] = []
    for section in split_sections(body):
        text = "\n\n".join(section)
        if len(text) <= budget:
            units.append(text)
            continue
        for block in section:
            units.extend([block] if len(block) <= budget else hard_split(block, budget))
    return units


def split_sections(body: str) -> list[list[str]]:
    sections: list[list[str]] = [[]]
    for block in split_blocks(body):
        if HEADING.match(block) and sections[-1]:
            sections.append([])
        sections[-1].append(block)
    return [section for section in sections if section]


def split_blocks(body: str) -> list[str]:
    blocks: list[str] = []
    lines: list[str] = []
    in_code = False
    for line in body.splitlines():
        if line.lstrip().startswith(FENCE):
            in_code = not in_code
        if not line.strip() and not in_code:
            if lines:
                blocks.append("\n".join(lines))
                lines = []
            continue
        lines.append(line)
    if lines:
        blocks.append("\n".join(lines))
    return blocks


def hard_split(text: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for line in text.split("\n"):
        for part in split_at_spaces(line, limit):
            candidate = f"{current}\n{part}" if current else part
            if len(candidate) <= limit:
                current = candidate
            else:
                pieces.append(current)
                current = part
    if current:
        pieces.append(current)
    return pieces


def split_at_spaces(line: str, limit: int) -> list[str]:
    parts: list[str] = []
    while len(line) > limit:
        cut = line.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(line[:cut].rstrip())
        line = line[cut:].lstrip()
    parts.append(line)
    return parts
