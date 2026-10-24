# Z innej planety → RSS

Kanał RSS audycji **„Z innej planety”** (Polskie Radio RDC) do słuchania w Apple Podcasts.

> Jest to cykl audycji popularyzujący naukę na antenie RDC. Trzygodzinna opowieść „z innej planety”. Nasze studio odwiedzają goście – najczęściej naukowcy. Prowadzimy też Radiowy Instytut Badań Akustycznych, w którym rozkładamy dźwięk na czynniki pierwsze. Natomiast w ostatniej godzinie rozwiązujemy kryminalną zagadkę lateralną. Zaprasza Łukasz Badowski.
>
> Więcej na RDC: https://www.rdc.pl/public/podcast/z-innej-planety_fY7TF0S0caRGGuoABNJe?episode=1SsoWBCT5DJvsOjwPqBg

*Od autora:* jako wierny słuchacz stworzyłem ten kanał RSS, żeby popularyzować audycję „Z innej planety”, która przynosi mi skojarzenia z programem „Sonda”. Kanał jest prywatną, niekomercyjną inicjatywą. Wszystkie prawa do audycji należą do Polskiego Radia RDC.

**Adres kanału:** https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml

Kanał jest synchronizowany automatycznie raz w tygodniu, **we wtorek po zakończeniu audycji** (o 23:59).

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
.venv/bin/rdc verify                                   # sprawdź pliki MP3 najnowszych odcinków
.venv/bin/rdc import-archive --from-page 1 --to-page 40   # archiwum, partiami
```

Synchronizację poza harmonogramem uruchomisz w GitHub: *Actions → Aktualizacja kanału → Run workflow*.

Publikacja ręczna:

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
