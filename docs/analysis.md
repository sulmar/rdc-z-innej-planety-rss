# Analiza techniczna: źródło danych rdc.pl

Dokumenty powiązane: [vision.md](vision.md), [requirements.md](requirements.md)

Stan na: 2026-10-24. Wynika z ręcznej analizy strony audycji
`https://www.rdc.pl/podcast/z-innej-planety_fY7TF0S0caRGGuoABNJe`.

## 1. Dostępność serwisu

| Adres | Wynik |
|---|---|
| `https://www.rdc.pl/podcast/...` | **403**, blokada Cloudflare „Just a moment…” (JS challenge) |
| `https://rdc.pl/podcast/...` | 403, jak wyżej |
| `https://web.rdc.pl/podcast/...` | **200**, pełny HTML strony, bez blokady |
| `https://www.rdc.pl/feed` | 200, RSS, ale tylko z **newsami** serwisu, bez podcastów |
| `https://www.rdc.pl/sitemaps/sitemap_1.xml` | 403 (Cloudflare) |
| `/wp-json/`, `/podcast/feed`, `/podcasty` (www) | 403 |
| `https://www.rdc.pl/brepo/...mp3` i `https://web.rdc.pl/brepo/...mp3` | 200, `audio/mpeg` |

**Wnioski:**
- RDC nie udostępnia API ani RSS podcastów. Jedynym źródłem jest HTML.
- Źródłem danych jest `web.rdc.pl`. To nieoficjalna ścieżka, więc adres bazowy musi być konfigurowalny.
- Do plików MP3 Cloudflare dopuszcza ruch także przez `www.rdc.pl`. Tego hosta używamy w `enclosure`, bo jest „kanoniczny”.

## 2. Schemat adresów URL

### Audycja (podcast)
```
/podcast/{slug}_{podcastId}
/podcast/z-innej-planety_fY7TF0S0caRGGuoABNJe
```
- `slug` jest opisowy i nieistotny dla routingu.
- `podcastId` to 20 znaków `[A-Za-z0-9]` i jednoznacznie identyfikuje audycję.

### Strona listy odcinków
```
/podcast/{slug}_{podcastId}?active_page={N}
```
- N = 1 to najnowsze odcinki.
- Na stronę przypada ok. 10 odcinków.
- Liczba stron jest w atrybucie `data-pagescount` (dla tej audycji: 159 stron, nagłówek „Odcinki podcastu (1589)”).

### Odcinek
```
/podcast/{slug}_{podcastId}?episode={episodeId}[&active_page={N}]
```
- `episodeId` to 20 znaków `[A-Za-z0-9]`, np. `LVHL34Ee9ix5OGapcwGo`. **Stały identyfikator, używany jako `guid`.**
- `active_page` steruje tylko listą wyświetlaną pod odtwarzaczem.
- Bez parametru `episode` strona pokazuje w odtwarzaczu najnowszy odcinek.

### Plik audio
```
/brepo/panel_repo/{YYYY}/{MM}/{DD}/{dir6}/{nazwa}.mp3
/brepo/panel_repo/2026/10/20/hy1hxq/zagadka-lateralna-2010.mp3
```
- `dir6` to losowy 6-znakowy katalog, a `nazwa` jest dowolna. **Adresu nie da się wyliczyć z `episodeId`**, trzeba go odczytać ze strony odcinka.
- Nagłówki: `Content-Type: audio/mpeg`, `Content-Length` (np. 69 321 153 B), `Accept-Ranges: bytes`. Przewijanie działa.

### Obrazy
- Repozytorium jest to samo: `/brepo/panel_repo/...`.
- Warianty rozmiaru są zakodowane w nazwie: `anchor_photo_front_1200x630_*`, `*_540x768_*`, `*_100x100_*`, `contain-1000-1000-max-*`.
- mod_pagespeed przepisuje część adresów na `x{nazwa}.pagespeed.ic.{hash}.jpg`. Lepiej używać `og:image`, który ma czysty, absolutny URL.

## 3. Struktura HTML

### 3.1 Lista odcinków (strona `?active_page=N`)

Kontener: `.myajaxlist_content[data-pagescount]`. W nim `li > .ranking_box.podcast_player_box` na każdy odcinek.

| Dane | Selektor | Przykład |
|---|---|---|
| tytuł | `.desc h3` | `Omawiamy: Nobel z chemii` |
| opis (HTML) | `.desc .lead` (`display:none`) | `<p>Gość: prof. …</p>` |
| data | `.podcast_time li.date p` | `20.10.2026` |
| czas trwania | `.podcast_time li.read_time p` | `51 min 15 s` |
| miniatura | `.ranking_box_left_content .image` → `background-image:url(...)` | 100×100 |
| `episodeId` | `.ranking_box_right a[href*="episode="]` | `LVHL34Ee9ix5OGapcwGo` |

**Pułapka:** element aktualnie odtwarzany (`.podcast_player_box.active`, „Teraz odtwarzane”) **nie ma linku `episode=`**. Jego ID trzeba wziąć z `meta[property="og:url"]` albo pobrać stronę `?active_page=N&episode=<inny>`.

Poza listą na stronie są linki `episode=` do **innych audycji** (sekcje polecane). Trzeba filtrować po `podcastId`.

### 3.2 Strona odcinka (`?episode=ID`)

| Dane | Selektor |
|---|---|
| **MP3** | `video.media_player > source[type="audio/mpeg"]` → `src` (ścieżka względna) |
| tytuł | `.main_title_value` lub `meta[property="og:title"]` |
| data | `.podcast_date_value` |
| czas trwania | `.player_desc .read_time` |
| prowadzący | `.author_value .name p` (np. `Łukasz Badowski`) |
| krótki opis | `.broadcast_box .title_item3` |
| opis skrócony | `meta[property="og:description"]` |
| okładka | `meta[property="og:image"]` (1200×630) |
| kanoniczny URL | `meta[property="og:url"]` |

### 3.3 Dane audycji
- nazwa: `.podcast_title h1`
- opis: `.podcast_short_desc`, `.podcast_desc`
- kategoria: `a[href^="/szczegoly-kategorii/"]`

## 4. Mapowanie na RSS

| Element RSS | Źródło | Uwagi |
|---|---|---|
| `channel/title` | `h1` audycji | |
| `channel/description` | `.podcast_short_desc` | |
| `channel/link` | URL audycji (www) | |
| `channel/itunes:image` | okładka audycji | Apple wymaga 1400–3000 px. Może być potrzebna własna grafika. |
| `channel/itunes:author` | „Polskie Radio RDC” | |
| `channel/language` | `pl` | |
| `channel/itunes:block` | `yes` | nie indeksować w katalogu Apple |
| `item/guid` (`isPermaLink="false"`) | `episodeId` | nigdy się nie zmienia |
| `item/title` | `h3` / `og:title` | dekodować encje (`&nbsp;`) |
| `item/link` | `https://www.rdc.pl/podcast/{slug}_{podcastId}?episode={id}` | |
| `item/pubDate` | data `DD.MM.YYYY` | brak godziny, patrz niżej |
| `item/description` | `.lead` | HTML w CDATA; obrazki względne → absolutne |
| `item/enclosure@url` | `source[src]` + `https://www.rdc.pl` | |
| `item/enclosure@length` | `Content-Length` z HEAD | |
| `item/enclosure@type` | `audio/mpeg` | |
| `item/itunes:duration` | `48 min 08 s` → `00:48:08` | |
| `item/itunes:image` | `og:image` | |
| `item/itunes:author` | prowadzący | |

**Godzina w `pubDate`:** jako godzinę przyjmujemy 12:00 Europe/Warsaw. Odcinki z tego samego dnia dostają malejące przesunięcie sekundowe według pozycji na liście, żeby zachować kolejność z rdc.pl.

## 5. Algorytm aktualizacji

```
stan = wczytaj episodes.json            # cache: episodeId → metadane + mp3 + length
dla N = 1..maxPages:
    html = GET {base}/podcast/{slug}_{id}?active_page=N
    odcinki = parsuj listę (filtr po podcastId, ID aktywnego z og:url)
    nowe = odcinki bez wpisu w stanie
    jeśli brak nowych i N ≥ 1 → przerwij   # tryb przyrostowy
    dla każdego nowego:
        html = GET ...?episode={id}         # pauza 1–2 s
        mp3 = source[src]; meta = og:*, autor
        length = HEAD mp3 → Content-Length
        stan[id] = …
zapisz episodes.json
wygeneruj feed.xml z episodes.json (sort: pubDate desc)
waliduj (min. 1 item, każdy z enclosure) → w przeciwnym razie nie publikuj
```

- **Import archiwum** to jednorazowe uruchomienie z `maxPages = data-pagescount`: ok. 159 + 1589 ≈ 1750 zapytań. Przy pauzie 1 s zajmuje to ok. 30 min, więc można je rozłożyć na kilka przebiegów.
- **Tryb przyrostowy** to zwykle 1 zapytanie o listę i 0–2 o odcinki.

## 6. Hostowanie: GitHub Actions + GitHub Pages

**Decyzja:** generator działa jako zaplanowany workflow GitHub Actions, a kanał jest publikowany jako plik statyczny na GitHub Pages.

```
.github/workflows/update-feed.yml   (cron: wtorek 23:59 czasu polskiego + workflow_dispatch)
  └─ checkout → rdc sync/verify/build → commit data/ i public/ → push public/ na gałąź gh-pages
Adres kanału: https://www.sulmar.pl/rdc-z-innej-planety-rss/feed.xml
```

| Aspekt | Uwagi |
|---|---|
| Koszt | Darmowe dla repozytorium publicznego. Pages z prywatnego repo wymaga płatnego planu. |
| Stan | `episodes.json` w repozytorium (commit przez workflow). Daje historię zmian i odporność na awarię. |
| Harmonogram | Raz w tygodniu, wtorek 23:59 (dzień emisji). `schedule` w Actions bywa opóźniony o kilkanaście minut lub więcej. |
| Wyłączanie crona | W repo publicznym GitHub wyłącza zaplanowane workflow po 60 dniach bez aktywności. Commity `episodes.json` przy nowych odcinkach liczą się jako aktywność. Przy dłuższej przerwie w audycji (np. wakacje) warto dodać okresowy commit „heartbeat” albo monitorować status workflow. |
| Cloudflare | Runnery GitHub to adresy IP centrów danych, które Cloudflare może traktować surowiej. **Pierwszy krok wdrożenia:** sprawdzić, czy `web.rdc.pl` odpowiada 200 z runnera. |
| Powiadomienia | Błąd workflow → domyślny e-mail od GitHub (spełnia N4). Dodatkowo krok kończący się błędem, gdy parser zwróci 0 odcinków. |
| N3 (bez psucia kanału) | Deploy na Pages tylko po pozytywnej walidacji. W przeciwnym razie zostaje poprzednia wersja. |
| Prywatność | Adres Pages jest publiczny, ale nieindeksowany: `itunes:block`, brak linków, opcjonalnie trudna do odgadnięcia nazwa pliku. |

## 7. Ryzyka techniczne

| Ryzyko | Wykrycie | Reakcja |
|---|---|---|
| Zmiana klas CSS w szablonie | 0 odcinków lub brak `source[src]` → workflow failuje | aktualizacja selektorów; testy na zapisanych próbkach HTML |
| `web.rdc.pl` zablokowane | kod 403 / strona „Just a moment” | zmiana adresu bazowego; plan B: Playwright w Actions |
| Blokada IP runnerów GitHub | jak wyżej, tylko w Actions | self-hosted runner lub inny host generatora; Pages zostaje |
| Zmiana URL pliku MP3 | okresowy HEAD ostatnich N enclosure | aktualizacja URL przy zachowaniu `guid` |
| Brak godziny publikacji | n/d | stała godzina + przesunięcie wg kolejności |
