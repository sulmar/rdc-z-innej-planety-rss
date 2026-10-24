# Z innej planety → RSS

Kanał RSS audycji **„Z innej planety”** (Polskie Radio RDC) do słuchania w Apple Podcasts.

**Adres kanału:** https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml

## Instalacja

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Użycie

```sh
.venv/bin/rdc run                                      # sync + build
.venv/bin/rdc sync                                     # nowe odcinki → data/episodes.json
.venv/bin/rdc build                                    # → public/feed.xml
.venv/bin/rdc validate                                 # sprawdź kanał
.venv/bin/rdc import-archive --from-page 1 --to-page 40   # archiwum, partiami
```

Publikacja kanału:

```sh
FEED_URL=https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml .venv/bin/rdc run
git commit -am "Aktualizacja kanału" && git push
git subtree push --prefix public origin gh-pages
```

## Odsłuch na iPhonie

1. Otwórz aplikację **Podcasty**.
2. **Biblioteka → ⋯ (prawy górny róg) → Obserwuj program wg adresu URL**.
3. Wklej `https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml` i zatwierdź.

Szczegóły: [docs/](docs/architecture.md)
