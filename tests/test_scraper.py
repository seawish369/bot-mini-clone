from kb.scraper import fetch_articles, make_session


def test_follows_next_page_and_skips_drafts(session):
    articles = fetch_articles(session=session)

    assert [a.id for a in articles] == [360051234567, 360000002222]
    assert len(session.urls) == 2
    assert "per_page=100" in session.urls[0]


def test_limit_stops_before_the_next_page(session):
    articles = fetch_articles(limit=1, session=session)

    assert len(articles) == 1
    assert len(session.urls) == 1


def test_article_fields_are_cleaned(articles):
    first = articles[0]

    assert first.title == "How to add a YouTube video"
    assert first.html_url.endswith("/360051234567-How-to-add-a-YouTube-video")
    assert first.updated_at == "2026-09-14T10:02:11Z"
    assert first.body.startswith("<p>You can play")


def test_session_retries_rate_limits_and_server_errors():
    retry = make_session().get_adapter("https://support.optisigns.com").max_retries

    assert retry.total == 5
    assert {429, 500, 502, 503, 504} <= set(retry.status_forcelist)
    assert retry.respect_retry_after_header
