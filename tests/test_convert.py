import pytest

from kb.convert import DROP_CLASS_HINTS, DROP_TAGS, html_to_markdown

CHROME_HTML = {
    "script": "<script>track('Drop me')</script>",
    "style": "<style>.drop-me { color: red }</style>",
    "noscript": "<noscript>Drop me</noscript>",
    "form": "<form><label>Drop me</label></form>",
    "button": "<button>Drop me</button>",
    "input": '<input value="Drop me">',
    "select": "<select><option>Drop me</option></select>",
    "nav": '<nav><a href="/hc/en-us">Drop me</a></nav>',
    "header": "<header>Drop me</header>",
    "footer": "<footer>Drop me</footer>",
    "aside": "<aside>Drop me</aside>",
}

CHROME_CLASSES = {
    "breadcrumb": "breadcrumbs",
    "article-votes": "article-votes",
    "article-share": "article-share",
    "related-articles": "related-articles",
    "advert": "Advertisement",
    "ads-": "ads-banner",
    "cookie": "cookie-consent",
}


def test_every_dropped_tag_and_class_hint_has_a_case():
    assert set(CHROME_HTML) == set(DROP_TAGS)
    assert set(CHROME_CLASSES) == set(DROP_CLASS_HINTS)


@pytest.mark.parametrize("tag", DROP_TAGS)
def test_page_chrome_tags_are_dropped(tag):
    md = html_to_markdown(f"<p>Keep me</p>{CHROME_HTML[tag]}<p>Keep me too</p>")

    assert md == "Keep me\n\nKeep me too\n"


@pytest.mark.parametrize("hint", DROP_CLASS_HINTS)
def test_widgets_are_dropped_by_class(hint):
    md = html_to_markdown(f'<p>Keep me</p><div class="widget {CHROME_CLASSES[hint]}"><p>Drop me</p></div>')

    assert md == "Keep me\n"


def test_nested_widgets_are_dropped():
    md = html_to_markdown(
        '<div class="article-share"><div class="cookie-banner"><button>Drop me</button></div></div><p>Keep me</p>'
    )

    assert md == "Keep me\n"


def test_content_that_mentions_chrome_words_is_kept():
    md = html_to_markdown('<p class="wysiwyg-text-align-left">Clear your cookies, then open the header and footer settings.</p>')

    assert md == "Clear your cookies, then open the header and footer settings.\n"


def test_keeps_structure_and_drops_page_chrome():
    md = html_to_markdown(
        '<h2>Add the app</h2><p>Open&nbsp;<a href="/hc/en-us/articles/1-files">Files</a></p><p>&nbsp;</p>'
        "<ol><li>One</li><li>Two<ul><li>Nested</li></ul></li></ol>"
        '<div class="article-votes">Was this helpful?</div><script>x()</script><nav>Home</nav>'
    )

    assert md == "## Add the app\n\nOpen [Files](/hc/en-us/articles/1-files)\n\n1. One\n2. Two\n   - Nested\n"


def test_relative_links_stay_relative_and_protocol_relative_urls_get_https():
    md = html_to_markdown('<p><a href="/hc/en-us/articles/2-x">x</a> <a href="#Setup">Setup</a></p><img src="//cdn.example.com/a.png" alt="a">')

    assert "[x](/hc/en-us/articles/2-x)" in md
    assert "[Setup](#Setup)" in md
    assert "![a](https://cdn.example.com/a.png)" in md


def test_code_blocks_keep_language_and_line_breaks():
    md = html_to_markdown('<pre><code class="language-bash">echo hi<br># comment</code></pre>')

    assert md == "```bash\necho hi\n# comment\n```\n"


def test_auto_language_is_not_written():
    md = html_to_markdown('<pre><code class="language-auto">https://example.com/callback</code></pre>')

    assert md == "```\nhttps://example.com/callback\n```\n"


def test_iframes_become_links():
    md = html_to_markdown(
        '<p><iframe src="//www.youtube.com/embed/abc"></iframe></p>'
        '<iframe src="https://www.canva.com/design/x/view?embed"></iframe>'
        "<iframe></iframe>"
    )

    assert "[Video: https://www.youtube.com/embed/abc](https://www.youtube.com/embed/abc)" in md
    assert "[Embedded content: https://www.canva.com/design/x/view?embed]" in md


def test_callouts_become_blockquotes_but_real_tables_stay_tables():
    md = html_to_markdown(
        "<table><tr><td><strong>TIP</strong></td></tr><tr><td><p>Use Live Schedule.</p></td></tr></table>"
        "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
    )

    assert md.startswith("> **TIP**\n>\n> Use Live Schedule.\n")
    assert "| A | B |" in md
    assert "| 1 | 2 |" in md


def test_headings_have_no_bold_and_h1_becomes_h2():
    md = html_to_markdown("<h1>Intro</h1><h3><strong>Step 1</strong></h3>")

    assert md == "## Intro\n\n### Step 1\n"


def test_html_shown_as_text_is_escaped_but_code_is_left_alone():
    md = html_to_markdown(
        "<p>Paste &lt;iframe src=\"x\"&gt; here, or use <code>&lt;b&gt;</code>. 2 &lt; 3.</p>"
        "<pre><code>&lt;iframe src=\"y\"&gt;&lt;/iframe&gt;</code></pre>"
    )

    assert '\\<iframe src="x">' in md
    assert "`<b>`" in md
    assert "2 < 3" in md
    assert '```\n<iframe src="y"></iframe>\n```' in md


def test_base64_images_are_dropped():
    md = html_to_markdown('<p>Scan this<img src="data:image/png;base64,AAAA" alt="qr"></p>')

    assert md == "Scan this\n"


def test_line_breaks_without_empty_backslash_lines():
    md = html_to_markdown("<p>Line one<br>Line two<br><br></p>")

    assert md == "Line one\\\nLine two\n"


def test_empty_input_gives_empty_document():
    assert html_to_markdown("") == "\n"
