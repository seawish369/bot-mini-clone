from dataclasses import replace

from kb.document import build_document, slug_for, slugify


def test_document_has_front_matter_title_and_citable_url(articles):
    doc = build_document(articles[0])

    assert doc.markdown.startswith(
        "---\n"
        'title: "How to add a YouTube video"\n'
        "article_id: 360051234567\n"
        "url: https://support.optisigns.com/hc/en-us/articles/360051234567-How-to-add-a-YouTube-video\n"
        "updated_at: 2026-09-14T10:02:11Z\n"
        "---\n\n"
        "# How to add a YouTube video\n\n"
        "Article URL: https://support.optisigns.com/hc/en-us/articles/360051234567-How-to-add-a-YouTube-video\n\n"
        "You can play YouTube videos"
    )
    assert "## Add the YouTube app" in doc.markdown
    assert "Was this article helpful?" not in doc.markdown


def test_slug_and_filename_come_from_the_article_url(articles):
    doc = build_document(articles[0])

    assert doc.slug == "360051234567-how-to-add-a-youtube-video"
    assert doc.filename == "360051234567-how-to-add-a-youtube-video.md"


def test_slug_falls_back_to_id_and_title(articles):
    odd = replace(articles[0], html_url="https://support.optisigns.com/hc/articles/no-number")

    assert slug_for(odd) == "360051234567-how-to-add-a-youtube-video"


def test_slugify_drops_accents_and_punctuation():
    assert slugify("What’s Needed? Café & Co.") == "whats-needed-cafe-co"


def test_titles_with_quotes_stay_valid_yaml(articles):
    doc = build_document(articles[1])

    assert 'title: "Using the \\"OptiSigns\\" API"' in doc.markdown


def test_content_hash_is_stable_and_changes_with_content(articles):
    article = articles[0]
    original = build_document(article).content_hash

    assert build_document(article).content_hash == original
    assert build_document(replace(article, body=article.body + "<p>New</p>")).content_hash != original
    assert build_document(replace(article, title="New title")).content_hash != original
    assert len(original) == 16


def test_content_hash_ignores_metadata_only_changes(articles):
    article = articles[0]

    assert build_document(replace(article, updated_at="2027-01-01T00:00:00Z")).content_hash == build_document(article).content_hash
