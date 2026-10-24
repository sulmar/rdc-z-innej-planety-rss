"""CLI: python -m rdc {sync,import-archive,build,validate,run}."""

from __future__ import annotations

import argparse
import logging
import sys

import httpx

from . import store
from .client import HttpClient, SourceBlockedError
from .config import Config
from .feed import build_feed, feed_episodes
from .parser import ParseError
from .sync import SyncResult, sync
from .validate import count_items, validate_feed, validate_file

log = logging.getLogger("rdc")


class CommandError(RuntimeError):
    pass


def _client(config: Config) -> HttpClient:
    return HttpClient(user_agent=config.user_agent, delay_s=config.request_delay_s)


def _report(result: SyncResult) -> None:
    log.info("Pobrane strony listy: %d, nowe odcinki: %d, uzupełnione: %d, nieudane: %d",
             result.pages_fetched, len(result.new), len(result.completed), len(result.failed))
    if result.failed and not result.completed:
        raise CommandError(f"Nie udało się pobrać żadnego pliku MP3 ({len(result.failed)} odcinków)")


def cmd_sync(config: Config, args: argparse.Namespace) -> None:
    state = store.load(config.data_path)
    max_pages = args.max_pages or config.max_pages_incremental
    with _client(config) as client:
        result = sync(client, config, state, to_page=max_pages)
    store.save(state, config.data_path)
    _report(result)


def cmd_import_archive(config: Config, args: argparse.Namespace) -> None:
    state = store.load(config.data_path)
    with _client(config) as client:
        result = sync(
            client, config, state,
            from_page=args.from_page, to_page=args.to_page, stop_when_no_new=False,
            on_page_done=lambda page: store.save(state, config.data_path),
        )
    store.save(state, config.data_path)
    _report(result)
    pages = state.podcast.pages_count if state.podcast else None
    log.info("W stanie: %d odcinków (stron na rdc.pl: %s)", len(state.episodes), pages or "?")


def cmd_build(config: Config, args: argparse.Namespace) -> None:
    state = store.load(config.data_path)
    xml_text = build_feed(state, config)

    previous = None
    if config.output_path.exists() and not args.force:
        previous = count_items(config.output_path.read_text(encoding="utf-8")) or None
    errors = validate_feed(xml_text, previous_count=previous)
    if errors:
        raise CommandError("Kanał nie przeszedł walidacji, poprzednia wersja pozostaje bez zmian:\n  "
                           + "\n  ".join(errors))

    store.write_atomic(config.output_path, xml_text)
    log.info("Zapisano %s (%d odcinków)", config.output_path, len(feed_episodes(state, config)))


def cmd_validate(config: Config, args: argparse.Namespace) -> None:
    errors = validate_file(config.output_path)
    if errors:
        raise CommandError("Błędy walidacji:\n  " + "\n  ".join(errors))
    log.info("%s: OK", config.output_path)


def cmd_run(config: Config, args: argparse.Namespace) -> None:
    cmd_sync(config, args)
    cmd_build(config, args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rdc",
                                     description="Kanał RSS audycji „Z innej planety” (Polskie Radio RDC).")
    parser.add_argument("-v", "--verbose", action="store_true", help="szczegółowe logi (każde zapytanie)")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("sync", help="pobierz nowe odcinki do data/episodes.json")
    p.add_argument("--max-pages", type=int, help="limit przeglądanych stron listy")
    p.set_defaults(func=cmd_sync)

    p = commands.add_parser("import-archive", help="pobierz archiwum odcinków (wznawialne)")
    p.add_argument("--from-page", type=int, default=1)
    p.add_argument("--to-page", type=int, help="domyślnie ostatnia strona")
    p.set_defaults(func=cmd_import_archive)

    p = commands.add_parser("build", help="wygeneruj public/feed.xml ze stanu")
    p.add_argument("--force", action="store_true", help="pomiń porównanie z poprzednią liczbą odcinków")
    p.set_defaults(func=cmd_build)

    p = commands.add_parser("validate", help="sprawdź public/feed.xml")
    p.set_defaults(func=cmd_validate)

    p = commands.add_parser("run", help="sync + build")
    p.add_argument("--max-pages", type=int)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(message)s", stream=sys.stderr)
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        args.func(Config.from_env(), args)
    except SourceBlockedError as exc:
        log.error("Źródło zablokowane: %s. Sprawdź RDC_BASE_URL.", exc)
        return 2
    except httpx.HTTPError as exc:
        log.error("Błąd sieci: %s", exc)
        return 1
    except (CommandError, ParseError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
