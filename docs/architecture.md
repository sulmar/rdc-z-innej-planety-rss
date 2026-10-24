# Architektura: „Z innej planety” w Apple Podcasts

Dokumenty powiązane: [vision.md](vision.md), [requirements.md](requirements.md), [analysis.md](analysis.md)

## 1. Przegląd

System jest **statycznym generatorem kanału RSS**. Nie ma serwera aplikacyjnego, bazy danych ani interfejsu użytkownika.

- **Wykonanie:** cyklicznie w GitHub Actions.
- **Stan:** plik JSON w repozytorium.
- **Wynik:** statyczny `feed.xml` na GitHub Pages.
- **Odtwarzanie:** w całości Apple Podcasts, które pobiera MP3 bezpośrednio z serwerów RDC.

```mermaid
flowchart LR
    subgraph RDC["Polskie Radio RDC"]
        WEB["web.rdc.pl<br/>strony HTML audycji"]
        MP3["www.rdc.pl/brepo<br/>pliki MP3 i obrazy"]
    end

    subgraph GH["GitHub"]
        CRON(["Actions: cron co 3 h<br/>+ uruchomienie ręczne"])
        GEN["Generator<br/>(Python)"]
        STATE[("data/episodes.json<br/>w repozytorium")]
        PAGES["GitHub Pages<br/>feed.xml"]
    end

    subgraph IPHONE["iPhone"]
        AP["Apple Podcasts"]
    end

    CRON --> GEN
    GEN -- "GET listy i odcinków" --> WEB
    GEN -- "HEAD (rozmiar)" --> MP3
    GEN <--> STATE
    GEN -- "deploy" --> PAGES
    AP -- "odpytuje RSS" --> PAGES
    AP -- "strumień / pobranie<br/>(Range)" --> MP3
```

Najważniejsza cecha: **pliki audio nigdy nie przechodzą przez nasz system** (W2.9). Kanał zawiera tylko metadane i odnośniki.

Diagram pokazuje docelowy stan po etapie 2. Etap 1 obejmuje tylko narzędzie CLI (blok „Generator”), uruchamiane ręcznie.

## 1a. Etapy realizacji

### Etap 1: narzędzie CLI (zrealizowany: 2026-10-24, opis użycia w [README](../README.md))
Cel: narzędzie uruchamiane ręcznie, które pobiera listę odcinków audycji i generuje poprawny kanał RSS.

| W zakresie | Poza zakresem (etap 2) |
|---|---|
| Komponenty z §3: `client`, `parser`, `models`, `store`, `sync`, `feed`, `validate` | Cron w GitHub Actions (§5.1 automatycznie, §5.3) |
| CLI: `sync`, `build`, `validate`, `import-archive` | Automatyczny deploy na Pages i commit stanu przez workflow |
| Stan w `data/episodes.json` i wynik w `public/feed.xml` (lokalnie) | Heartbeat przeciw wyłączaniu crona |
| Testy jednostkowe na próbkach HTML (§10) | Alerty e-mail z nieudanych workflow |
| Workflow `test.yml` (opcjonalnie) | |

**Użycie w etapie 1:**
```
python -m generator sync            # pobierz nowe odcinki → data/episodes.json
python -m generator build           # data/episodes.json → public/feed.xml
python -m generator validate        # sprawdź public/feed.xml
python -m generator run             # sync + build
```

**Test na iPhonie w etapie 1:** Apple Podcasts potrzebuje publicznego adresu HTTPS. Wygenerowany `feed.xml` publikujemy ręcznie: commit do repozytorium i `git subtree push --prefix public origin gh-pages`; GitHub Pages w trybie „Deploy from a branch” (`gh-pages` / root), bez własnego workflow. Kanał odświeża się tylko wtedy, gdy ręcznie uruchomimy narzędzie i zrobimy commit.

**Kryterium ukończenia etapu 1:**
- Po `sync` i `build` kanał przechodzi `validate` i zewnętrzny walidator.
- Kanał dodany w Apple Podcasts pokazuje listę odcinków (W1) i pozwala je odtwarzać z zapamiętaniem pozycji (W2).
- Ponowne uruchomienie bez nowych odcinków daje identyczny `feed.xml` (idempotentność).

### Etap 2: automatyzacja
- Workflow `update-feed.yml` z cronem: §5.1 i §7.
- Weryfikacja MP3: §5.3.
- Spełnienie W1.8 (nowy odcinek w ciągu 6 h) i N4 (alerty).

Projekt CLI w etapie 1 nie zależy od GitHub Actions. Workflow w etapie 2 tylko wywołuje te same polecenia, więc nie wymaga zmian w kodzie generatora.

## 2. Decyzje architektoniczne

| # | Decyzja | Uzasadnienie | Odrzucone alternatywy |
|---|---|---|---|
| D1 | Statyczny `feed.xml` zamiast dynamicznego endpointu | Brak serwera do utrzymania, darmowy hosting, wysoka dostępność (N1, N6) | Funkcja serverless (koszt, cold start, sekrety), własny VPS |
| D2 | GitHub Actions + Pages | Decyzja użytkownika; darmowe, wbudowane alerty e-mail (N4) | Cloudflare Workers + KV, AWS Lambda + S3 |
| D3 | Stan jako JSON w repozytorium | Wersjonowanie i historia zmian, łatwy podgląd i ręczna korekta, brak zewnętrznej bazy | SQLite (binarne diffy), cache Actions (ulotny), baza zewnętrzna |
| D4 | Python ≥ 3.12 + `httpx` + `BeautifulSoup` (`html.parser`), XML przez `xml.etree` | Dojrzałe biblioteki do HTML, prosty kod, szybki start w Actions | Node.js (cheerio), Go (więcej kodu przy parsowaniu) |
| D5 | Kanał budowany zawsze w całości ze stanu | Generacja jest deterministyczna i idempotentna, więc ponowne uruchomienie nic nie psuje | Doklejanie itemów do istniejącego XML |
| D6 | `guid` = `episodeId` z RDC | Stabilny, unikalny, niezależny od URL MP3 (W1.10, W2.4) | Hash URL MP3, URL strony |
| D7 | Deploy tylko po walidacji | Zepsuta aktualizacja zostawia poprzedni kanał (N3) | Publikacja bez kontroli |

## 3. Komponenty

```
generator/
├── config.py       konfiguracja (adres bazowy, podcastId, limity)
├── client.py       HTTP: User-Agent, timeouty, pauzy, ponowienia
├── parser.py       HTML → modele (lista odcinków, strona odcinka, audycja)
├── models.py       Podcast, Episode (dataclasses)
├── store.py        odczyt/zapis data/episodes.json
├── sync.py         logika aktualizacji: wykrycie nowych, uzupełnienie danych
├── feed.py         modele → RSS 2.0 + iTunes (XML)
├── validate.py     sprawdzenie wygenerowanego kanału
└── __main__.py     CLI: sync | build | validate | import-archive
```

| Komponent | Odpowiedzialność | Zależy od |
|---|---|---|
| **client** | Jedyne miejsce z ruchem sieciowym. Pauza 1–2 s między zapytaniami, 3 ponowienia z backoff, wykrywanie strony Cloudflare („Just a moment”) jako osobnego błędu | config |
| **parser** | Czyste funkcje `html → model`, bez sieci. Selektory z [analysis.md §3](analysis.md#3-struktura-html) w jednym miejscu | models |
| **store** | Atomowy zapis (plik tymczasowy, potem rename), stabilna kolejność kluczy (czytelne diffy) | models |
| **sync** | Orkiestracja: pobiera strony listy, kończy przy pierwszej stronie bez nowych odcinków, dla nowych pobiera stronę odcinka i robi HEAD MP3 | client, parser, store |
| **feed** | Zawsze buduje całość ze stanu (D5). Normalizuje daty, czasy trwania, absolutne URL-e w opisach | models |
| **validate** | Reguły z §6. Kończy się kodem ≠ 0, gdy kanał jest niepoprawny | — |

Rozdzielenie **parser** (czysty) i **client** (sieć) pozwala testować parsowanie na zapisanych próbkach HTML bez dostępu do rdc.pl.

## 4. Model danych

### `data/episodes.json`
```json
{
  "podcast": {
    "id": "fY7TF0S0caRGGuoABNJe",
    "slug": "z-innej-planety",
    "title": "Z innej planety",
    "description": "…",
    "image": "https://…/cover.jpg",
    "updated_at": "2026-10-24T15:00:00+02:00"
  },
  "episodes": {
    "LVHL34Ee9ix5OGapcwGo": {
      "title": "Omawiamy: Nobel z chemii",
      "date": "2026-10-20",
      "order": 1,
      "duration_s": 3075,
      "author": "Łukasz Badowski",
      "description_html": "<p>Kenso Soai i Henri B. Kagan…</p>",
      "image": "https://www.rdc.pl/brepo/panel_repo/…_1200x630_….jpg",
      "mp3_url": "https://www.rdc.pl/brepo/panel_repo/2026/10/20/wo79bb/z-innej-planety-2010.mp3",
      "mp3_length": 69321153,
      "first_seen": "2026-10-20T18:00:00+02:00",
      "checked_at": "2026-10-24T15:00:00+02:00"
    }
  }
}
```

- Klucz słownika `episodes` to `episodeId`, czyli `guid` (D6).
- `order` to pozycja w obrębie dnia na liście RDC. Służy do wyliczenia godziny w `pubDate` (12:00 Europe/Warsaw minus `order` sekund).
- `first_seen` i `checked_at` służą do diagnostyki i okresowej weryfikacji MP3.
- Szacowany rozmiar przy ok. 1600 odcinkach to 2–4 MB, co jest akceptowalne w repozytorium.

### Artefakt: `public/feed.xml`
- RSS 2.0 z przestrzeniami nazw `itunes`, `content` i `atom`.
- Mapowanie pól według [analysis.md §4](analysis.md#4-mapowanie-na-rss).
- `<itunes:block>yes</itunes:block>`, żeby kanał nie trafił do katalogu Apple.
- `<atom:link rel="self">` wskazuje na adres Pages.

## 5. Przepływy

### 5.1 Aktualizacja (etap 1: ręcznie; etap 2: cyklicznie co 3 h)
```mermaid
sequenceDiagram
    participant A as GitHub Actions
    participant G as Generator
    participant R as web.rdc.pl
    participant S as episodes.json
    participant P as GitHub Pages

    A->>G: python -m generator sync
    G->>S: wczytaj stan
    loop strony 1..N, dopóki są nowe odcinki
        G->>R: GET ?active_page=N
        R-->>G: HTML listy
    end
    loop każdy nowy odcinek
        G->>R: GET ?episode=ID
        R-->>G: HTML odcinka (MP3, og:*)
        G->>R: HEAD mp3
    end
    G->>S: zapisz stan
    A->>G: build + validate
    alt walidacja OK
        A->>A: git commit episodes.json (jeśli zmiana)
        A->>P: deploy public/feed.xml
    else błąd
        A-->>A: workflow failed → e-mail
    end
```

Typowy przebieg wysyła 1 zapytanie o listę i 0–2 o odcinki, co spełnia N2.

### 5.2 Import archiwum (jednorazowy)
- Uruchamiany ręcznie (`workflow_dispatch` z parametrem `pages`) lub lokalnie: `python -m generator import-archive --from-page 1 --to-page 40`.
- Działa partiami, np. po 40 stron (ok. 440 zapytań, ok. 10 min). Po każdej partii zapisuje stan, więc przerwany import można wznowić.
- Odcinki już obecne w stanie są pomijane.

### 5.3 Weryfikacja MP3 (etap 2, raz w tygodniu)
- Wysyła HEAD dla ostatnich 20 odcinków.
- Przy kodzie 404 pobiera ponownie stronę odcinka i aktualizuje `mp3_url`, zachowując `guid`.

## 6. Walidacja przed publikacją

Kanał nie jest publikowany (N3), jeśli zachodzi którykolwiek z warunków:
- liczba odcinków jest równa 0 albo mniejsza niż w poprzedniej wersji (ochrona przed częściowym parsowaniem);
- któryś item nie ma `guid`, `title`, `pubDate` lub `enclosure` z `url` i `length > 0`;
- `guid` się powtarzają;
- XML jest niepoprawny składniowo;
- strona listy RDC zwróciła 0 odcinków albo stronę Cloudflare. Jest to błąd, a nie „brak nowości”.

## 7. CI/CD i infrastruktura (etap 2)

### Repozytorium
```
.github/workflows/
├── update-feed.yml     cron "0 */3 * * *", workflow_dispatch
├── verify-mp3.yml      cron tygodniowy
└── test.yml            push/PR: testy jednostkowe
data/episodes.json      stan (commitowany przez workflow)
generator/              kod
tests/fixtures/*.html   zapisane próbki stron RDC
public/                 artefakt Pages (nie commitowany; budowany w workflow)
docs/                   dokumentacja
```

### Workflow `update-feed.yml`: kroki
1. `checkout`, `setup-python` z cache zależności.
2. **Sprawdzenie dostępności źródła** (pierwsze ryzyko z analizy): `client` rozpoznaje stronę Cloudflare i kończy krok czytelnym błędem.
3. `sync`, `build`, `validate`.
4. Commit `data/episodes.json`, tylko gdy plik się zmienił. Autor: `github-actions[bot]`.
5. `actions/upload-pages-artifact`, potem `actions/deploy-pages`.
6. `concurrency: feed`, żeby dwa przebiegi nie działały równocześnie.

### Uprawnienia
- `contents: write` (commit stanu), `pages: write`, `id-token: write` (deploy Pages).
- Brak sekretów: wszystkie źródła są publiczne.

### Ciągłość działania
- GitHub wyłącza crona po 60 dniach bez aktywności w repo.
  - Commity stanu przy nowych odcinkach zwykle temu zapobiegają.
  - Dodatkowo `update-feed.yml` aktualizuje `podcast.updated_at` raz w miesiącu, nawet bez nowych odcinków (commit „heartbeat”).

## 8. Konfiguracja

| Parametr | Domyślnie | Opis |
|---|---|---|
| `RDC_BASE_URL` | `https://web.rdc.pl` | źródło HTML (N5) |
| `RDC_MEDIA_BASE_URL` | `https://www.rdc.pl` | host w `enclosure` i obrazkach |
| `PODCAST_PATH` | `z-innej-planety_fY7TF0S0caRGGuoABNJe` | audycja; w przyszłości lista |
| `REQUEST_DELAY_S` | `1.5` | pauza między zapytaniami |
| `MAX_PAGES_INCREMENTAL` | `3` | limit stron w trybie przyrostowym |
| `FEED_MAX_ITEMS` | brak | opcjonalne obcięcie archiwum w kanale |
| `FEED_URL` | `https://{user}.github.io/{repo}/feed.xml` | `atom:link self` |

Zmienne ustawia się jako `vars` repozytorium w GitHub, bez zmian w kodzie.

## 9. Obsługa błędów i obserwowalność

| Sytuacja | Zachowanie |
|---|---|
| Timeout lub 5xx z RDC | 3 ponowienia z backoff, potem błąd workflow |
| Strona Cloudflare / 403 | Natychmiastowy błąd z komunikatem „źródło zablokowane” |
| Brak `source[src]` na stronie odcinka | Odcinek pomijany w tym przebiegu (log ostrzeżenia), ponowna próba przy następnym. Jeśli dotyczy wszystkich nowych odcinków, workflow kończy się błędem |
| Walidacja nieudana | Brak deployu, błąd workflow |
| Błąd workflow | E-mail od GitHub (N4); szczegóły w logach Actions |

Logi to zwykły tekst w Actions: liczba pobranych stron, nowe odcinki (ID + tytuł), czas trwania przebiegu.

## 10. Testowanie

- **Jednostkowe (parser):** zapisane próbki HTML z `tests/fixtures` pokrywają stronę listy, stronę odcinka, element „Teraz odtwarzane” bez linku i stronę Cloudflare.
- **Jednostkowe (feed):** deterministyczny XML dla zadanego stanu (snapshot), konwersje czasu i dat.
- **Walidacja zewnętrzna:** ręcznie po pierwszym wdrożeniu, przez Podcasts Connect / castfeedvalidator.
- **Akceptacja:** scenariusze z [requirements.md](requirements.md), sprawdzane ręcznie na iPhonie.

## 11. Rozszerzalność

- **Inne audycje RDC:** `PODCAST_PATH` → lista, stan `data/{podcastId}.json`, kanał `public/{slug}.xml`. Parser się nie zmienia, bo wszystkie audycje mają ten sam szablon.
- **Plan B przy blokadzie Cloudflare:** dodatkowa implementacja `client` oparta na Playwright (przeglądarka headless w Actions) za tym samym interfejsem. Pozostałe komponenty bez zmian.
- **Inne aplikacje podcastowe** (Overcast, Pocket Casts) działają od razu, bo kanał jest standardowym RSS.
