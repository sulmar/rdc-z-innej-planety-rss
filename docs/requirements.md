# Wymagania: „Z innej planety” w Apple Podcasts

Dokumenty powiązane: [vision.md](vision.md), [analysis.md](analysis.md)

## Kontekst i podział odpowiedzialności

Zgodnie z wizją nie budujemy własnego odtwarzacza. Za interfejs i odtwarzanie odpowiada **Apple Podcasts** na iPhonie. Za dane odpowiada **nasz system, czyli generator kanału RSS**. Każde wymaganie poniżej mówi więc:

- **co widzi i robi użytkownik** w Apple Podcasts,
- **co musi zapewnić kanał RSS**, żeby to działało.

Oznaczenia: **[APP]** to funkcja Apple Podcasts, **[RSS]** to obowiązek naszego systemu.

---

## W1. Przeglądanie listy audycji

### Historyjka
> Jako słuchacz chcę zobaczyć listę odcinków „Z innej planety”, od najnowszych, z tytułem, datą, czasem trwania i opisem, żeby szybko wybrać odcinek do odsłuchania.

### Wymagania funkcjonalne

| ID | Wymaganie | Typ |
|---|---|---|
| W1.1 | Lista odcinków jest posortowana od najnowszego do najstarszego. | [APP] / [RSS]: poprawny `pubDate` |
| W1.2 | Każdy odcinek ma tytuł zgodny z tytułem na rdc.pl. | [RSS] `item/title` |
| W1.3 | Każdy odcinek ma datę publikacji. Kilka odcinków z tego samego dnia zachowuje kolejność z rdc.pl. | [RSS] `pubDate` z sekundowym przesunięciem wg pozycji na liście |
| W1.4 | Każdy odcinek ma czas trwania. | [RSS] `itunes:duration` (format `HH:MM:SS`) |
| W1.5 | Każdy odcinek ma opis z informacją o gościu i zachowanym formatowaniem (akapity, linki). | [RSS] `description` / `content:encoded` (HTML w CDATA) |
| W1.6 | Każdy odcinek ma okładkę. Gdy jej brak, wyświetla się okładka audycji. | [RSS] `itunes:image` w `item` i w `channel` |
| W1.7 | Audycja ma nazwę, opis, prowadzącego i okładkę widoczne na stronie programu. | [RSS] `channel/title`, `description`, `itunes:author`, `itunes:image` (min. 1400×1400) |
| W1.8 | *(etap 2)* Nowy odcinek pojawia się na liście najpóźniej **6 godzin** po publikacji na rdc.pl. W etapie 1 pojawia się po ręcznym uruchomieniu narzędzia. | [RSS] cykliczna aktualizacja |
| W1.9 | Z odcinka da się przejść do jego strony na rdc.pl. | [RSS] `item/link` |
| W1.10 | Odcinek, który już widziałem, nie pojawia się ponownie jako nowy ani się nie dubluje. | [RSS] stały `guid` = `episodeId` z RDC |
| W1.11 | Lista obejmuje archiwum ze skonfigurowanego okresu (domyślnie: wszystkie dostępne odcinki). | [RSS] konfigurowalny zakres |
| W1.12 | Mogę subskrybować audycję i dostać powiadomienie o nowym odcinku. | [APP] / [RSS]: dostępny publiczny URL HTTPS |

### Kryteria akceptacji
- Po dodaniu adresu kanału w Apple Podcasts (*Obserwuj program wg adresu URL*) widzę audycję „Z innej planety” z okładką i opisem.
- Pierwsze 10 odcinków na liście w aplikacji odpowiada pierwszej stronie listy na rdc.pl: te same tytuły, daty i kolejność.
- Ponowne wygenerowanie kanału bez nowych odcinków nie zmienia listy w aplikacji.
- Kanał przechodzi walidację (Podcasts Connect lub castfeedvalidator) bez błędów.

---

## W2. Odtwarzanie, zatrzymywanie, wznawianie, zapamiętywanie miejsca

### Historyjka
> Jako słuchacz chcę odtworzyć odcinek, zatrzymać go w dowolnym momencie i później wznowić od tego samego miejsca, również po zamknięciu aplikacji, na innym urządzeniu albo offline.

### Wymagania funkcjonalne

| ID | Wymaganie | Typ |
|---|---|---|
| W2.1 | Wybranie odcinka uruchamia odtwarzanie w ciągu kilku sekund. | [APP] / [RSS]: `enclosure` z bezpośrednim, publicznym URL MP3 |
| W2.2 | Mogę zatrzymać i wznowić odtwarzanie, także z ekranu blokady, Centrum sterowania, CarPlay i słuchawek. | [APP] |
| W2.3 | Mogę przewijać do dowolnego miejsca oraz skakać o 15/30 s. | [APP] / [RSS]: serwer MP3 obsługuje `Range` (zweryfikowane: `Accept-Ranges: bytes`) |
| W2.4 | Aplikacja zapamiętuje miejsce zatrzymania i wznawia od niego, także po zamknięciu aplikacji i restarcie telefonu. | [APP] / [RSS]: stały `guid` i niezmienny URL `enclosure` |
| W2.5 | Pozycja odsłuchu synchronizuje się między urządzeniami Apple (iPhone, iPad, Mac). | [APP] przez iCloud / [RSS]: jak W2.4 |
| W2.6 | Mogę pobrać odcinek i słuchać go offline. | [APP] / [RSS]: poprawne `enclosure length` i `type="audio/mpeg"` |
| W2.7 | Odsłuchany odcinek jest oznaczany jako odtworzony. | [APP] / [RSS]: `itunes:duration` zgodny z rzeczywistą długością |
| W2.8 | Mogę zmienić prędkość odtwarzania. | [APP] |
| W2.9 | Odtwarzany jest oryginalny plik audio RDC, bez rekompresji i bez kopiowania na inne serwery. | [RSS] `enclosure url` wskazuje na `/brepo/panel_repo/...` RDC |

### Wymagania dotyczące stabilności (krytyczne dla W2.4 i W2.5)
- **Raz nadany `guid` odcinka nigdy się nie zmienia.** Zmiana `guid` powoduje utratę zapamiętanej pozycji i powielenie odcinka.
- **URL `enclosure` istniejącego odcinka nie zmienia się** bez potrzeby. Jest zapisywany w cache przy pierwszym przetworzeniu.
- Jeśli RDC zmieni lokalizację pliku, system aktualizuje URL, ale zachowuje `guid`.

### Kryteria akceptacji
- Odcinek zatrzymany w 20. minucie i wznowiony po wymuszonym zamknięciu aplikacji startuje od 20. minuty.
- Odcinek zatrzymany na iPhonie wznawia się od tego samego miejsca na drugim urządzeniu zalogowanym na to samo Apple ID.
- Pobrany odcinek odtwarza się w trybie samolotowym.
- Przewinięcie na koniec 50-minutowego odcinka działa bez pobierania całego pliku.
- Po kolejnej aktualizacji kanału zapamiętane pozycje odsłuchu pozostają bez zmian.

---

## Wymagania niefunkcjonalne

| ID | Wymaganie |
|---|---|
| N1 | Kanał jest dostępny pod stałym adresem HTTPS (GitHub Pages), z dostępnością ≥ 99% w miesiącu. |
| N2 | Aktualizacja wysyła do rdc.pl najwyżej kilkanaście zapytań, z wyjątkiem jednorazowego importu archiwum. Między zapytaniami jest pauza. |
| N3 | Nieudana aktualizacja nie psuje opublikowanego kanału: zostaje poprzednia poprawna wersja. |
| N4 | Gdy parser zwróci 0 odcinków lub błąd, narzędzie kończy się kodem błędu i komunikatem. W etapie 2 wysyłane jest dodatkowo powiadomienie. |
| N5 | Adres bazowy rdc.pl (`web.rdc.pl` / `www.rdc.pl`) jest konfigurowalny. |
| N6 | Koszt utrzymania jest bliski zera. |

## Poza zakresem
- Własny odtwarzacz, aplikacja iOS lub interfejs WWW. Te funkcje zapewnia Apple Podcasts.
- Wyszukiwanie po treści odcinków i transkrypcje.
- Inne audycje RDC (możliwe rozszerzenie w przyszłości).
