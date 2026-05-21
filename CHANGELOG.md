# Changelog

Zmiany od dodania profili gracza.

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
- Dodano zapis ustawień do `%APPDATA%\ValoPicker\settings.json`.
- Dodano obsługę `--live`, żeby jednorazowo wymusić tryb live niezależnie od ustawień.
- Argument `--refresh` może jednorazowo nadpisać zapisany interwał odświeżania.

### Terminal i EXE

- Poprawiono obsługę kodowania konsoli dla polskich znaków.
- Dodano ustawianie tytułu okna i próbę ustawienia czcionki konsoli na `Consolas`.
- Potwierdzono, że problem z brakującymi polskimi znakami może wynikać z czcionki CMD.
- Dodano build samodzielnego pliku `dist\ValoPicker.exe`.
- Dodano `ValoPicker.spec`, `build_exe.ps1`, `requirements-build.txt` i instrukcję `BUILD_EXE.md`.
- Po zmianach przebudowano `dist\ValoPicker.exe`.

### Live i menu

- Uproszczono menu live.
- Usunięto osobną opcję `View Recommendation`, bo dublowała widok `View Pre-Game (Agent Select) Players`.
- Ekran live jest mniej przeładowany i mocniej eksponuje rekomendację w Agent Select.
- Manual mode nie kończy już od razu pracy po pokazaniu wyniku, więc da się spokojnie odczytać rekomendację.

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
