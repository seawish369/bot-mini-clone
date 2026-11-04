import re

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

DROP_TAGS = ("script", "style", "noscript", "form", "button", "input", "select", "nav", "header", "footer", "aside")
DROP_CLASS_HINTS = ("breadcrumb", "article-votes", "article-share", "related-articles", "advert", "ads-", "cookie")
VIDEO_HOSTS = ("youtube", "vimeo", "wistia", "loom")
BLOCK_TAGS = ("p", "ul", "ol", "div", "pre", "table", "blockquote")
CONTENT_TAGS = ("img", "iframe", "table", "pre")
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

TAG_LIKE = re.compile(r"<(?=[a-zA-Z/!])")


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    drop_page_chrome(soup)
    replace_iframes(soup)
    fix_images_and_links(soup)
    callouts_to_blockquotes(soup)
    clean_headings(soup)
    keep_code_line_breaks(soup)
    escape_html_text(soup)
    drop_empty_blocks(soup)

    converter = MarkdownConverter(
        heading_style="ATX",
        bullets="-",
        newline_style="backslash",
        code_language_callback=code_language,
    )
    markdown = converter.convert_soup(soup)

    markdown = markdown.replace("\u00a0", " ")
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"^[ \t]*\\\n", "\n", markdown, flags=re.MULTILINE)
    markdown = re.sub(r"\\\n(?=[ \t]*\n)", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def drop_page_chrome(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.decomposed:
            continue
        classes = " ".join(tag.get("class") or []).lower()
        if any(hint in classes for hint in DROP_CLASS_HINTS):
            tag.decompose()


def replace_iframes(soup: BeautifulSoup) -> None:
    for iframe in soup.find_all("iframe"):
        src = absolute_protocol(iframe.get("src") or "")
        if not src:
            iframe.decompose()
            continue
        label = "Video" if any(host in src for host in VIDEO_HOSTS) else "Embedded content"
        link = soup.new_tag("a", href=src)
        link.string = f"{label}: {src}"
        paragraph = soup.new_tag("p")
        paragraph.append(link)
        iframe.replace_with(paragraph)


def fix_images_and_links(soup: BeautifulSoup) -> None:
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("data:"):
            img.decompose()
        elif src:
            img["src"] = absolute_protocol(src)

    for link in soup.find_all("a", href=True):
        link["href"] = absolute_protocol(link["href"])


def absolute_protocol(url: str) -> str:
    return f"https:{url}" if url.startswith("//") else url


def callouts_to_blockquotes(soup: BeautifulSoup) -> None:
    for table in soup.find_all("table"):
        rows = [row.find_all(("td", "th")) for row in table.find_all("tr")]
        if not rows or any(len(cells) > 1 for cells in rows):
            continue

        quote = soup.new_tag("blockquote")
        for cells in rows:
            for cell in cells:
                if not cell.get_text(strip=True) and not cell.find("img"):
                    continue
                block = soup.new_tag("div" if cell.find(BLOCK_TAGS) else "p")
                block.extend(list(cell.contents))
                quote.append(block)
        table.replace_with(quote)


def clean_headings(soup: BeautifulSoup) -> None:
    for heading in soup.find_all(HEADING_TAGS):
        if heading.name == "h1":
            heading.name = "h2"
        for bold in heading.find_all(("strong", "b")):
            bold.unwrap()


def keep_code_line_breaks(soup: BeautifulSoup) -> None:
    for br in soup.select("pre br"):
        br.replace_with("\n")


def escape_html_text(soup: BeautifulSoup) -> None:
    for text in soup.find_all(string=TAG_LIKE):
        if text.find_parent(("code", "pre")):
            continue
        text.replace_with(NavigableString(TAG_LIKE.sub(r"\\<", text)))


def drop_empty_blocks(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(("p", "div", "span")):
        if tag.decomposed:
            continue
        if not tag.get_text(strip=True) and not tag.find(CONTENT_TAGS):
            tag.decompose()


def code_language(pre: Tag) -> str:
    code = pre.find("code")
    if not isinstance(code, Tag):
        return ""
    for cls in code.get("class") or []:
        if cls.startswith("language-") and cls != "language-auto":
            return cls.removeprefix("language-")
    return ""
