# Wizja: „Z innej planety” w Apple Podcasts

## Problem

Regularnie słucham audycji **„Z innej planety”** Polskiego Radia RDC. Odcinki są dostępne tylko na stronie rdc.pl i w oficjalnej aplikacji RDC. Oba kanały są niewygodne i zawodne:

- aplikacja działa niestabilnie i nie zapamiętuje postępu odsłuchu;
- nie ma subskrypcji ani powiadomień o nowych odcinkach;
- nie da się pobrać odcinka i słuchać go offline, np. w samochodzie lub metrze;
- strona www stoi za zabezpieczeniem Cloudflare i źle działa na telefonie;
- archiwum (ok. 1600 odcinków) da się przeglądać tylko po 10 pozycji na stronę.

RDC nie publikuje kanału RSS tej audycji, więc nie można jej dodać do żadnej standardowej aplikacji podcastowej.

## Wizja

> Odcinki „Z innej planety” same pojawiają się w Apple Podcasts na moim iPhonie, tak jak każdy inny podcast: z subskrypcją, pobieraniem, zapamiętaną pozycją i synchronizacją między urządzeniami.

Rozwiązanie to **automatycznie aktualizowany kanał RSS** (zgodny z Apple Podcasts). Budujemy go na podstawie publicznie dostępnych stron audycji na rdc.pl. W aplikacji Podcasts dodaje się go raz, przez *Biblioteka → … → Obserwuj program wg adresu URL*. Od tej chwili korzystam z odcinków wyłącznie w natywnej aplikacji Apple.

## Użytkownik

- **Główny:** ja, stały słuchacz z iPhone'em i Apple Podcasts.
- **Ewentualnie:** kilka znajomych osób, którym przekażę adres kanału. Rozwiązanie nie jest przeznaczone do publicznej dystrybucji.

## Zakres

### W zakresie
1. Cykliczne (np. co kilka godzin) sprawdzanie strony audycji i wykrywanie nowych odcinków.
2. Dla każdego odcinka pobranie tytułu, opisu, daty, czasu trwania, prowadzącego, okładki i adresu pliku MP3.
3. Wygenerowanie poprawnego kanału RSS 2.0 z rozszerzeniami `itunes:`:
   - `enclosure` z adresem MP3, typem i rozmiarem;
   - `guid` oparty na stałym identyfikatorze odcinka z RDC;
   - link do oryginalnej strony odcinka na rdc.pl.
4. Udostępnienie kanału pod stałym, publicznym adresem HTTPS, który Apple Podcasts może odpytywać.
5. Zapamiętywanie już przetworzonych odcinków, żeby nie pobierać ich ponownie.
6. Opcjonalne jednorazowe zaimportowanie archiwum, w całości lub od wybranej daty.

### Poza zakresem
- Kopiowanie lub ponowne hostowanie plików audio: kanał wskazuje na oryginalne MP3 na serwerach RDC.
- Zgłaszanie podcastu do publicznego katalogu Apple Podcasts. Prawa do treści należą do Polskiego Radia RDC.
- Własna aplikacja mobilna lub odtwarzacz.
- Inne audycje RDC. Architektura może jednak pozwalać dodać je później, bo każdy podcast ma ten sam schemat adresu: `/podcast/{slug}_{id}`.

## Kryteria sukcesu

- Nowy odcinek pojawia się w Apple Podcasts najpóźniej kilka godzin po publikacji na rdc.pl.
- Odcinek da się odtworzyć, przewinąć i pobrać offline na iPhonie.
- Kanał przechodzi walidację, np. Podcasts Connect lub castfeedvalidator.
- Działa bez mojej interwencji przez co najmniej kilka tygodni.
- Gdy zmieni się struktura strony RDC i aktualizacja się nie powiedzie, dostaję powiadomienie, zamiast cichej awarii.

## Założenia i ograniczenia

- Źródłem danych jest HTML stron audycji. RDC nie udostępnia API ani RSS (szczegóły: [analysis.md](analysis.md)).
- `www.rdc.pl` jest chronione przez Cloudflare. Obecnie bez blokady działa host `web.rdc.pl`. To nieoficjalna ścieżka i może przestać działać.
- Adres MP3 jest dostępny tylko na stronie konkretnego odcinka, więc każdy nowy odcinek wymaga osobnego zapytania.
- Strona podaje tylko datę publikacji, bez godziny.
- Usługa ma być tania lub darmowa w utrzymaniu i nie może obciążać serwerów RDC: rzadkie odpytywanie, cache, limit zapytań.

## Ryzyka

| Ryzyko | Skutek | Łagodzenie |
|---|---|---|
| Zmiana szablonu HTML na rdc.pl | Brak nowych odcinków | Testy parsera, alert przy pustym wyniku |
| Zamknięcie dostępu przez `web.rdc.pl` | Brak dostępu do danych | Konfigurowalny adres bazowy; plan B: przeglądarka headless |
| Zmiana lokalizacji plików MP3 | Niedziałające odcinki | Okresowa weryfikacja (HEAD) ostatnich enclosure |
| Kwestie praw autorskich | Konieczność wyłączenia | Użytek prywatny, brak redystrybucji audio, brak publicznego katalogu |

## Decyzje

- **Etapy:** etap 1 to narzędzie CLI uruchamiane ręcznie, które generuje kanał RSS z listy odcinków. Etap 2 dodaje automatyczną aktualizację (cron). Szczegóły w [architecture.md](architecture.md#1a-etapy-realizacji).
- **Hosting:** GitHub Pages (publikacja `feed.xml`); w etapie 2 dodatkowo GitHub Actions (cykliczna aktualizacja). Szczegóły w [analysis.md](analysis.md#6-hostowanie-github-actions--github-pages).

## Otwarte pytania

1. Ile archiwum umieścić w kanale: wszystkie ~1600 odcinków czy np. ostatni rok?
2. Czy kanał ma być ukryty, np. pod trudnym do odgadnięcia adresem?
3. Jakim kanałem dostawać powiadomienia o awarii?
