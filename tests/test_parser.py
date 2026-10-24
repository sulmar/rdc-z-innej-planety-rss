from datetime import date

import pytest

from rdc import parser
from rdc.client import is_cloudflare_challenge
from tests.conftest import MEDIA, PODCAST_ID, fixture


def test_list_page1_contains_ten_episodes_with_current_one_first():
    listing = parser.parse_episode_list(fixture("list_page1.html"), PODCAST_ID, MEDIA)

    assert listing.pages_count == 159
    assert len(listing.items) == 10
    first = listing.items[0]
    # Element „Teraz odtwarzane” nie ma linku – ID pochodzi z przycisku „skopiuj link”.
    assert first.id == "vUUo7CT1dEeqCtvPozVw"
    assert first.title == "Zagadka lateralna"
    assert first.date == date(2026, 10, 20)
    assert first.duration_s == 48 * 60 + 8
    assert listing.items[1].id == "LVHL34Ee9ix5OGapcwGo"
    assert listing.items[1].title == "Omawiamy: Nobel z chemii"


def test_list_ignores_episodes_of_other_podcasts_and_duplicates():
    for name in ("list_page1.html", "list_page2.html", "episode_LVHL34Ee9ix5OGapcwGo.html"):
        listing = parser.parse_episode_list(fixture(name), PODCAST_ID, MEDIA)
        ids = [item.id for item in listing.items]
        assert len(ids) == len(set(ids)) == 10
        assert "HGzovIm7Zr4v8PPToJRd" not in ids  # odcinek audycji „Bez ogródek”


def test_list_page2_has_no_current_episode():
    listing = parser.parse_episode_list(fixture("list_page2.html"), PODCAST_ID, MEDIA)
    assert listing.items[0].id == "73AmloiAdO9LPxeE6V3t"
    assert "vUUo7CT1dEeqCtvPozVw" not in [i.id for i in listing.items]


def test_active_episode_on_episode_page_is_the_requested_one():
    listing = parser.parse_episode_list(fixture("episode_LVHL34Ee9ix5OGapcwGo.html"), PODCAST_ID, MEDIA)
    assert [i.id for i in listing.items[:2]] == ["vUUo7CT1dEeqCtvPozVw", "LVHL34Ee9ix5OGapcwGo"]


def test_description_urls_are_absolute_and_without_pagespeed():
    listing = parser.parse_episode_list(fixture("list_page1.html"), PODCAST_ID, MEDIA)
    html = listing.items[0].description_html
    assert html.startswith("<p>W chemicznym nastroju")
    assert (
        'src="https://www.rdc.pl/brepo/panel_repo/2026/10/20/lrekki/contain-1000-1000-max-2026-10-20-chemia.png"'
        in html
    )
    assert 'class="lead"' not in html


def test_episode_page():
    details = parser.parse_episode_page(fixture("episode_LVHL34Ee9ix5OGapcwGo.html"), MEDIA)
    assert details.mp3_url == "https://www.rdc.pl/brepo/panel_repo/2026/10/20/wo79bb/z-innej-planety-2010.mp3"
    assert details.title == "Omawiamy: Nobel z chemii"
    assert details.author == "Łukasz Badowski"
    assert details.image == (
        "https://www.rdc.pl/brepo/panel_repo/2025/05/20/2nw5rh/anchor_photo_front_1200x630_mikrofon-rdc-1.jpg"
    )


def test_podcast_info():
    info = parser.parse_podcast(fixture("list_page1.html"), MEDIA)
    assert info.title == "Z innej planety"
    assert info.description.startswith("Jest to cykl audycji popularyzujący naukę")
    assert info.image == "https://www.rdc.pl/brepo/panel_repo/2025/10/02/2p9tlj/zinnejplanety.png"


def test_cloudflare_page_is_detected_and_not_parsed():
    html = fixture("cloudflare.html")
    assert is_cloudflare_challenge(403, html)
    assert not is_cloudflare_challenge(200, fixture("list_page1.html"))
    with pytest.raises(parser.ParseError):
        parser.parse_episode_list(html, PODCAST_ID, MEDIA)


@pytest.mark.parametrize(
    "text, expected",
    [("48 min 08 s", 2888), ("51 min 15 s", 3075), ("1 h 02 min 03 s", 3723), ("45 s", 45), ("", None)],
)
def test_parse_duration(text, expected):
    assert parser.parse_duration(text) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("/brepo/a/xanchor_photo_front_100x100_mikrofon-rdc-1.jpg.pagespeed.ce.FZbGEB5g7X.jpg",
         "/brepo/a/mikrofon-rdc-1.jpg"),
        ("/brepo/a/xcontain-540-768-max-zinnejplanety.png.pagespeed.ic.iD7DWIAVaw.png", "/brepo/a/zinnejplanety.png"),
        ("/brepo/a/zinnejplanety.png", "/brepo/a/zinnejplanety.png"),
    ],
)
def test_original_image_url(url, expected):
    assert parser.original_image_url(url) == expected


def test_absolute_url_moves_rdc_hosts_to_media_base():
    assert parser.absolute_url("https://web.rdc.pl/brepo/x.jpg", MEDIA) == "https://www.rdc.pl/brepo/x.jpg"
    assert parser.absolute_url("/brepo/x.jpg", MEDIA) == "https://www.rdc.pl/brepo/x.jpg"
    assert parser.absolute_url("https://example.com/a", MEDIA) == "https://example.com/a"


def test_normalize_newlines():
    assert parser.normalize_newlines("<p>a</p>\r\n<p>b</p>\r") == "<p>a</p>\n<p>b</p>\n"


def test_episode_page_with_empty_audio_source_has_no_mp3():
    html = fixture("episode_LVHL34Ee9ix5OGapcwGo.html").replace(
        'src="/brepo/panel_repo/2026/10/20/wo79bb/z-innej-planety-2010.mp3"', 'src=""')
    assert parser.parse_episode_page(html, MEDIA).mp3_url is None
