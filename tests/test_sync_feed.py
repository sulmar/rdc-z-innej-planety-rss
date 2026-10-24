import xml.etree.ElementTree as ET

from generator import store
from generator.__main__ import main
from generator.feed import NS, build_feed
from generator.sync import sync
from generator.validate import validate_feed
from tests.conftest import FakeClient, fixture


def _pages():
    return {1: fixture("list_page1.html"), 2: fixture("list_page2.html")}


def test_first_sync_fetches_details_for_new_episodes(config, fixed_now):
    state = store.load(config.data_path)
    client = FakeClient(config, _pages())

    result = sync(client, config, state, to_page=1, now=fixed_now)

    assert result.pages_fetched == 1
    assert len(result.new) == len(result.completed) == 10
    assert len(client.episode_requests) == 10
    assert state.podcast.title == "Z innej planety"
    assert state.podcast.pages_count == 159
    episode = state.episodes["LVHL34Ee9ix5OGapcwGo"]
    assert episode.mp3_url.endswith(".mp3") and episode.mp3_length == 1000
    assert episode.author == "Łukasz Badowski"


def test_incremental_sync_without_new_episodes_makes_no_episode_requests(config, fixed_now):
    state = store.load(config.data_path)
    sync(FakeClient(config, _pages()), config, state, to_page=1, now=fixed_now)

    client = FakeClient(config, _pages())
    result = sync(client, config, state, now=fixed_now)

    assert result.pages_fetched == 1  # strona 1 bez nowych → koniec
    assert result.new == [] and client.episode_requests == []


def test_incremental_sync_continues_to_next_page_while_new_episodes_appear(config, fixed_now):
    state = store.load(config.data_path)
    client = FakeClient(config, _pages())

    result = sync(client, config, state, to_page=2, now=fixed_now)

    assert result.pages_fetched == 2
    assert len(state.episodes) == 20


def test_episodes_without_mp3_size_are_retried_and_not_published(config, fixed_now):
    state = store.load(config.data_path)
    result = sync(FakeClient(config, _pages(), mp3_length=None), config, state, to_page=1, now=fixed_now)
    assert len(result.failed) == 10 and not result.completed
    assert not any(ep.is_complete for ep in state.episodes.values())

    client = FakeClient(config, _pages())
    result = sync(client, config, state, to_page=1, now=fixed_now)
    assert len(result.completed) == 10


def test_state_roundtrip(config, fixed_now):
    state = store.load(config.data_path)
    sync(FakeClient(config, _pages()), config, state, to_page=1, now=fixed_now)
    store.save(state, config.data_path)

    loaded = store.load(config.data_path)
    assert loaded == state


def test_feed_is_valid_ordered_and_deterministic(config, fixed_now):
    state = store.load(config.data_path)
    sync(FakeClient(config, _pages()), config, state, to_page=2, now=fixed_now)

    xml_text = build_feed(state, config)
    assert validate_feed(xml_text) == []
    store.save(state, config.data_path)
    assert build_feed(store.load(config.data_path), config) == xml_text

    channel = ET.fromstring(xml_text).find("channel")
    items = channel.findall("item")
    assert len(items) == 20
    assert channel.findtext(f"{{{NS['itunes']}}}block") == "Yes"
    assert channel.find(f"{{{NS['atom']}}}link").get("href") == config.feed_url
    assert channel.find(f"{{{NS['itunes']}}}category").get("text") == "Science"

    first, second = items[0], items[1]
    # Dwa odcinki z 20.10.2026 – kolejność jak na rdc.pl, różne godziny.
    assert first.findtext("guid") == "vUUo7CT1dEeqCtvPozVw"
    assert second.findtext("guid") == "LVHL34Ee9ix5OGapcwGo"
    assert first.findtext("pubDate") == "Tue, 20 Oct 2026 12:00:00 +0200"
    assert second.findtext("pubDate") == "Tue, 20 Oct 2026 11:59:59 +0200"
    assert second.findtext(f"{{{NS['itunes']}}}duration") == "00:51:15"
    assert second.findtext("link") == (
        "https://www.rdc.pl/podcast/z-innej-planety_fY7TF0S0caRGGuoABNJe?episode=LVHL34Ee9ix5OGapcwGo"
    )
    enclosure = second.find("enclosure")
    assert enclosure.get("type") == "audio/mpeg" and enclosure.get("length") == "1000"


def test_feed_max_items(config, fixed_now):
    from dataclasses import replace

    state = store.load(config.data_path)
    sync(FakeClient(config, _pages()), config, state, to_page=2, now=fixed_now)
    xml_text = build_feed(state, replace(config, feed_max_items=5))
    assert len(ET.fromstring(xml_text).findall("./channel/item")) == 5


def test_validate_reports_errors():
    assert validate_feed("<rss") != []
    assert "Kanał nie zawiera żadnego odcinka" in validate_feed(
        '<rss version="2.0"><channel><title>X</title></channel></rss>'
    )
    bad_item = (
        '<rss version="2.0"><channel><title>X</title>'
        "<item><title>A</title><guid>1</guid><pubDate>zła data</pubDate>"
        '<enclosure url="http://x/a.mp3" length="0" type="audio/mpeg"/></item>'
        "<item><title>B</title><guid>1</guid></item></channel></rss>"
    )
    errors = "\n".join(validate_feed(bad_item))
    for expected in ("pubDate", "https", "length", "zduplikowany guid", "brak enclosure"):
        assert expected in errors


def test_build_keeps_previous_feed_when_new_one_has_fewer_items(config, fixed_now, monkeypatch):
    state = store.load(config.data_path)
    sync(FakeClient(config, _pages()), config, state, to_page=2, now=fixed_now)
    store.save(state, config.data_path)
    monkeypatch.setenv("DATA_PATH", str(config.data_path))
    monkeypatch.setenv("OUTPUT_PATH", str(config.output_path))

    assert main(["build"]) == 0
    original = config.output_path.read_text()

    for episode_id in list(state.episodes)[:5]:
        del state.episodes[episode_id]
    store.save(state, config.data_path)

    assert main(["build"]) == 1
    assert config.output_path.read_text() == original
    assert main(["build", "--force"]) == 0
    assert main(["validate"]) == 0
