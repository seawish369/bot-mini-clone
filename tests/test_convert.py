from kb.convert import html_to_markdown


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
