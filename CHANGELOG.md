# Changelog

Zmiany od dodania profili gracza.

## 2026-05-25

### Internationalization / i18n

- Dodano pełne wsparcie dwóch języków aplikacji: `English` i `Polski`.
- Domyślnym językiem publicznej wersji jest `English`.
- Język można zmienić w `Settings`.
- Ustawienie języka jest zapisywane w `%APPDATA%\ValoPicker\settings.json`.
- Przetłumaczono widoczne elementy CMD: menu, status, manual mode, ekran live, rekomendacje, problemy, ostrzeżenia, porady i błędy normalizera.
- Dodano testy spójności słowników i18n, żeby `en` i `pl` miały ten sam zestaw kluczy.
- Poprawiono brakujące tłumaczenia PL w ekranie live/no-client: menu, komunikaty statusu, profil, interwał odświeżania i fallback `Unknown`.
- Przetłumaczono w PL stany picków `locked/selected` oraz etykietę `Lvl ?` w ekranie teamu.
- Rozszerzono dane strategiczne agent+mapa do struktury EN/PL, żeby angielski tryb nie korzystał z polskich notatek ani hardcodowanych wyjątków.
- Przeniesiono dane map tuning i synergie do `valo_picker/data/`.
- Dodano strukturalne `ReasonKind` dla powodów rekomendacji oraz strukturalne issue normalizera zamiast testowania logiki po gotowych stringach UI.
- Dodano `Agent.traits` i przeniesiono cechę `selfish` z osobnej listy do danych agenta.
- Dodano testy integralności danych strategicznych.

### Code cleanup

- Zebrano główne stałe scoringu rekomendera w jednym miejscu i opisano je jako heurystyczne wagi, a nie wartości probabilistyczne.
- Zoptymalizowano liczenie `team_score_after_pick`, żeby bazowe role i utility teamu nie były odbudowywane od zera dla każdego kandydata.
- Dodano komentarz przy `ssl._create_unverified_context()` wyjaśniający self-signed cert lokalnego API Riot Client.
- Dodano `requirements.txt` z informacją, że aplikacja nie ma zależności runtime poza standard library.

## 2026-05-21

### Profil gracza

- Dodano zapis profilu gracza w ustawieniach aplikacji.
- Profil jest używany w trybie ręcznym i live.
- Style profilu wpisuje się cyframi, np. `4,7` albo `4,7,8`.
- Usunięto import i eksport profilu z JSON, żeby ustawianie profilu było prostsze.
- Usunięto osobne pytanie o beginner mode. Teraz tryb początkujący włącza się numerem `8`.
- Teksty profilu w menu ustawień są zapisane bez polskich znaków, żeby CMD nie psuł wyświetlania na starszych czcionkach.

### Ustawienia aplikacji

- Dodano menu `Settings`.
- Dodano zapis `refresh_seconds` w zakresie 2-10 sekund.
- Dodano zapis domyślnego trybu startu: `Live`, `Manual` albo `Status`.
- Dodano ustawienie języka: domyślnie `English`, opcjonalnie `Polski`.
- Dodano zapis ustawień do `%APPDATA%\ValoPicker\settings.json`.
- Dodano obsługę `--live`, żeby jednorazowo wymusić tryb live niezależnie od ustawień.
- Argument `--refresh` może jednorazowo nadpisać zapisany interwał odświeżania.

### Terminal i EXE

- Poprawiono obsługę kodowania konsoli dla polskich znaków.
- Dodano ustawianie tytułu okna i próbę ustawienia czcionki konsoli na `Consolas`.
- Dodano próbę ustawienia domyślnego rozmiaru okna konsoli na `74x34`, żeby aplikacja nie startowała z przesadnie szerokim oknem.
- Potwierdzono, że problem z brakującymi polskimi znakami może wynikać z czcionki CMD.
- Dodano build samodzielnego pliku `dist\ValoPicker.exe`.
- Dodano `ValoPicker.spec`, `build_exe.ps1`, `requirements-build.txt` i instrukcję `BUILD_EXE.md`.
- Po zmianach przebudowano `dist\ValoPicker.exe`.

### Live i menu

- Uproszczono menu live.
- Usunięto osobną opcję `View Recommendation`, bo dublowała widok `View Pre-Game (Agent Select) Players`.
- Ekran live jest mniej przeładowany i mocniej eksponuje rekomendację w Agent Select.
- Manual mode nie kończy już od razu pracy po pokazaniu wyniku, więc da się spokojnie odczytać rekomendację.
- Manual mode pozwala wpisać `0`, `q`, `quit` albo `menu`, żeby wrócić do menu bez kończenia całego programu.

### Rekomendacje

- Wzmocniono priorytet controllera i smoke'ów jako najważniejszego braku w kompozycji.
- Wzmocniono priorytet inicjatora, gdy team nie ma info, flasha albo cleara pod execute.
- Profil gracza ma teraz mniejszy wpływ na wynik niż krytyczne braki kompozycji.
- Trzeci duelist jest mocniej karany.
- Selfish duelist przy istniejącym dueliście jest mocniej karany.
- Drugi sentinel bez smoke'ów albo inicjatora jest mocniej karany.
- Breeze, Icebox i Abyss mocniej premiują wall controllera.
- Bind, Split, Lotus i Sunset mocniej premiują clear, flash, stun i suppress.
- Powody rekomendacji są porządkowane tak, żeby najpierw pokazywać powód kompozycyjny lub mapowy, a dopiero potem profil gracza.

### Testy

- Dodano testy ustawień aplikacji.
- Dodano testy parsowania profilu z menu CLI.
- Dodano testy regresji rekomendera:
  - aggressive/solo queue nie może przepchnąć trzeciego duelista bez controllera,
  - brak smoke'ów wygrywa z profilem gracza,
  - brak inicjatora promuje support execute,
  - Abyss ze smoke'ami nadal premiuje wall controllera,
  - Split z core utility i bez duelista promuje Raze jako clear entry.
- Aktualny wynik testów: `python -m unittest discover -s tests` przechodzi.

### Dokumentacja

- Zaktualizowano `README.md` o ustawienia, profil gracza, build EXE i aktualny status projektu.
- Dodano `PROFILE_GUIDE.md` z opisem stylów profilu.
- Dodano `BUILD_EXE.md` z instrukcją budowania i testowania `.exe`.
- Dodano `META_NOTES.md` z notatkami o researchu i kierunku strojenia rekomendacji.
