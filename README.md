# Z innej planety → RSS

Generator prywatnego kanału RSS audycji **„Z innej planety”** Polskiego Radia RDC, do słuchania w Apple Podcasts.
Kanał zawiera tylko metadane i odnośniki do oryginalnych plików MP3 na serwerach RDC.

Dokumentacja: [wizja](docs/vision.md) · [wymagania](docs/requirements.md) · [analiza źródła](docs/analysis.md) · [architektura](docs/architecture.md)

**Adres kanału:** https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml

Etap 1 to narzędzie uruchamiane ręcznie. Automatyczna aktualizacja (cron w GitHub Actions) to etap 2.

## Instalacja

Wymagany Python ≥ 3.12.

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Użycie

```sh
.venv/bin/python -m rdc run              # sync + build: najczęstsze użycie
.venv/bin/python -m rdc sync             # nowe odcinki → data/episodes.json
.venv/bin/python -m rdc build            # data/episodes.json → public/feed.xml (z walidacją)
.venv/bin/python -m rdc validate         # sprawdź public/feed.xml
.venv/bin/python -m rdc import-archive --from-page 1 --to-page 40   # archiwum, partiami
```

Po instalacji to samo dostępne jest jako polecenie `rdc`, np. `.venv/bin/rdc run`.

- `sync` przegląda listę od najnowszych odcinków i kończy na pierwszej stronie bez nowości. Domyślnie przegląda najwyżej 3 strony (`--max-pages`).
- `import-archive` zapisuje stan po każdej stronie, więc przerwany import można wznowić od następnej strony. Całe archiwum to 159 stron, czyli ok. 1750 zapytań (ok. 45 min przy domyślnej pauzie).
- `build` nie nadpisze `public/feed.xml`, jeśli nowy kanał nie przejdzie walidacji lub ma mniej odcinków niż poprzedni. Opcja `--force` pomija porównanie liczby odcinków.
- `-v` pokazuje każde zapytanie HTTP.

Kody wyjścia: `0` OK, `1` błąd (parsowanie, sieć, walidacja), `2` źródło zablokowane przez Cloudflare.

### Konfiguracja (zmienne środowiskowe)

| Zmienna | Domyślnie |
|---|---|
| `RDC_BASE_URL` | `https://web.rdc.pl` (źródło HTML; `www.rdc.pl` jest za Cloudflare) |
| `RDC_MEDIA_BASE_URL` | `https://www.rdc.pl` (host w linkach, MP3 i obrazkach) |
| `PODCAST_PATH` | `z-innej-planety_fY7TF0S0caRGGuoABNJe` |
| `REQUEST_DELAY_S` | `1.5` |
| `MAX_PAGES_INCREMENTAL` | `3` |
| `FEED_MAX_ITEMS` | brak limitu |
| `FEED_URL` | brak; publiczny adres kanału (`atom:link rel="self"`) |
| `DATA_PATH`, `OUTPUT_PATH` | `data/episodes.json`, `public/feed.xml` |

## Publikacja i subskrypcja na iPhonie (etap 1, ręcznie)

GitHub Pages w trybie „Deploy from a branch” serwuje katalog główny gałęzi, więc `public/` publikujemy na osobnej gałęzi `gh-pages`:

```sh
FEED_URL=https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml .venv/bin/python -m rdc run
git add data public && git commit -m "Aktualizacja kanału"
git subtree push --prefix public origin gh-pages
```

W ustawieniach repozytorium wybierz *Settings → Pages → Deploy from a branch → `gh-pages` / root*.

Na iPhonie: **Podcasty → Biblioteka → ⋯ → Obserwuj program wg adresu URL**, wklej adres kanału.

Konto `sulmar` ma w GitHub Pages własną domenę, więc `sulmar.github.io/...` przekierowuje na `www.sulmar.pl/...`.

## Testy

```sh
.venv/bin/python -m pytest
```

Testy działają offline na zapisanych stronach RDC z `tests/fixtures/`. Po zmianie szablonu rdc.pl warto podmienić próbki i poprawić selektory w `rdc/parser.py`.
