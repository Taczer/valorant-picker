# Valo Picker

Valo Picker to lokalny asystent do wyboru agenta w Valorancie. Ten pierwszy etap działa w CMD i ma tryb ręczny: wybierasz mapę, wpisujesz obecny skład teamu, ustawiasz profil gry, a program liczy najlepszy pick i alternatywy.

Program nie wybiera i nie lockuje agentów. Nie klika w klienta gry, nie czyta pamięci gry i nie omija Vanguard. Docelowo ma wyłącznie odczytywać dane dostępne przez lokalny klient/API.

## Uruchomienie

```powershell
python -m valo_picker
```

Domyślne uruchomienie pokazuje ekran live-first w stylu CMD. Jeśli klient Valoranta albo agent select nie są dostępne, program pokaże status i menu z przejściem do trybu ręcznego.

W menu aplikacji opcja `4. Settings` zapisuje:

- częstotliwość odświeżania live w zakresie 2.0-10.0 sekund,
- domyślny tryb startu: `Live`, `Manual` albo `Status`,
- profil gracza: style wpisywane cyframi, np. `4,7` albo `4,7,8`.
- `--live` może jednorazowo wymusić ekran live, nawet gdy zapisano inny domyślny tryb.

Ustawienia trafiają do:

```text
%APPDATA%\ValoPicker\settings.json
```

Wymuszenie trybu ręcznego:

```powershell
python -m valo_picker --manual
```

Szybki test na przykładowym lobby:

```powershell
python -m valo_picker --sample
```

Status lokalnego klienta:

```powershell
python -m valo_picker --status
```

Wymuszenie ekranu live:

```powershell
python -m valo_picker --live
```

Budowanie pliku `.exe` bez wymagania Pythona u użytkownika:

```powershell
.\build_exe.ps1
```

Szczegóły są w [BUILD_EXE.md](BUILD_EXE.md).

Bezpieczny debug log bez tokenów:

```powershell
python -m valo_picker --status --debug
```

Instrukcja live odczytu teamu i rekomendacji znajduje się w [LIVE_USAGE.md](LIVE_USAGE.md).

Opis stylów profilu gracza znajduje się w [PROFILE_GUIDE.md](PROFILE_GUIDE.md).

Notatki meta map/agentów i źródła strojenia znajdują się w [META_NOTES.md](META_NOTES.md).

Historia zmian od dodania profili znajduje się w [CHANGELOG.md](CHANGELOG.md).

## Status projektu

Szacowany postęp całej docelowej aplikacji: **88%**.

Gotowe:

- **MVP CMD, tryb ręczny: 100%**
  - lokalna baza agentów i map,
  - analiza teamu,
  - wieloczynnikowy scoring kandydatów,
  - rekomendacja najlepszego picka i alternatyw.
- **Normalizacja Pre-Game: 100%**
  - adapter pod payload `pregame/v1/matches/{matchId}`,
  - mapowanie `MapID`, `CharacterID`, `CharacterSelectionState`,
  - ostrzeżenia dla nieznanych map/agentów.
- **Terminal UI w stylu CMD: 95%**
  - ekran `PRE-GAME (AGENT SELECT)`,
  - ekran `CURRENT GAME`,
  - skrócony ekran teamu, rekomendacji, problemów i menu,
  - nicki i agenci w aktywnym meczu,
  - porada do aktualnie granej postaci,
  - brak opcji auto-pick/lock.
- **Read-only integracja Riot/Valorant API: 100%**
  - lockfile,
  - wykrywanie procesu Valoranta,
  - region/shard,
  - PUUID,
  - PartyID,
  - MatchID,
  - Pre-Game Match,
  - Current Game Match,
  - nicki graczy przez Name Service,
  - client version,
  - nagłówki GLZ,
  - retry tokenów po 401/403,
  - odświeżanie domyślnie co 5 sekund,
  - bez zapisu tokenów na dysk.
- **Debug log bez tokenów: 100%**
  - endpoint i HTTP status,
  - status `AGENT_SELECT` / `IN_GAME`,
  - skrócone `MatchID` i `PartyID`,
  - warnings/errors normalizera,
  - maskowanie UUID w endpointach,
  - bez nagłówków auth i bez tokenów.
- **Settings: 90%**
  - zapis częstotliwości odświeżania,
  - zapis domyślnego trybu startu,
  - nadpisywanie refreshu argumentem `--refresh`,
  - wymuszanie live argumentem `--live`,
  - zapis profilu gracza.
- **Profil użytkownika: 100%**
  - zapis preferowanego stylu gry,
  - mieszanie stylów po przecinku, np. `4,7`,
  - tryb początkujący,
  - automatyczne użycie profilu w live i trybie ręcznym.
- **Build EXE: 100%**
  - PyInstaller `onefile` CMD build,
  - `dist\ValoPicker.exe`,
  - skrypt `build_exe.ps1`,
  - instrukcja `BUILD_EXE.md`,
  - test `--sample`, `--status` i debug log na gotowym `.exe`.
- **Test live na prawdziwym kliencie: 100%**
  - Agent Select działa na realnym lobby,
  - IN_GAME działa w aktywnym meczu,
  - team, nicki, agenci i porady są widoczne w CMD.

Do zrobienia:

- **Settings**
  - ręczne ustawienia regionu/fallback.
- **UI desktop/web**
  - dashboard,
  - panel Agent Select Assistant,
  - panel profilu i ustawień.
- **Strojenie danych**
  - dokładniejsze map-specific porady i priorytety agentów,
  - lepsze wagi scoringu dla brakującego entry/duelista,
  - aktualizacja agentów i map po testach.

## Etapy projektu

1. **MVP CMD, tryb ręczny**
   - lokalna baza agentów i map,
   - analiza ról i utility,
   - scoring kandydatów,
   - wynik w CMD: najlepszy pick, alternatywy, problemy teamu, oceny i porada.

2. **Normalizacja danych z Pre-Game**
   - adapter pod odpowiedzi `pregame/v1/matches/{matchId}`,
   - mapowanie `MapID`, `CharacterID`, `CharacterSelectionState`,
   - obsługa nieznanych map/agentów.

3. **Lokalna integracja Riot/Valorant Client API**
   - wykrywanie lockfile,
   - sprawdzenie czy Valorant działa,
   - pobranie regionu, shardu, PUUID, PartyID, MatchID,
   - odczyt pre-game lobby domyślnie co 5 sekund,
   - bez zapisu tokenów na dysk.

4. **Profil użytkownika**
   - styl gry,
   - tryb początkujący.

5. **UI desktop/web**
   - dashboard połączenia,
   - panel Agent Select Assistant,
   - panel mapy, teamu, rekomendacji i problemów,
   - ciemny gamingowy wygląd z czerwonymi akcentami,
   - bez oficjalnych grafik Valoranta.

6. **Testy i strojenie**
   - testy scoringu dla popularnych kompozycji,
   - walidacja map i agentów,
   - analiza debug logów po edge-case payloadach Riot API,
   - scenariusze fallback, gdy klient Valoranta nie działa.

## Algorytm rekomendacji

Rekomender nie działa jak prosta lista tierów. Każdy agent dostaje wynik z kilku warstw:

- **Dostępność picka** - agent wybrany albo zalockowany przez sojusznika dostaje bardzo dużą karę.
- **Presja ról** - controller, initiator, sentinel i duelist są ważone zależnie od braków teamu oraz mapy. Brak controllera ma najwyższy priorytet.
- **Brak entry/duelista** - jeśli team ma już podstawowe utility, ale nie ma agenta do otwierania site'u, Duelist dostaje mocny bonus.
- **Profil mapy** - każda mapa ma cechy typu `wall_map`, `three_sites`, `tight_chokes`, `mid_control`, `long_range`, `postplant`. Agent dostaje bonus, jeśli jego utility realnie odpowiada na te cechy.
- **Progi utility** - mapa definiuje minimalne potrzeby, np. smoke, wall, info, flash, flank watch, clear, stall albo post-plant. Algorytm nagradza agenta, który domyka brakujący próg.
- **Synergie teamu** - model wykrywa pary i układy, np. Raze + Fade/Breach na ciasnych mapach, Jett + Sova/KAY/O na otwartych liniach, Viper + Harbor na mapach wallowych albo controller + sentinel pod stabilną kontrolę mapy.
- **Ryzyko kompozycji** - trzeci duelist, drugi sentinel bez smoke'ów/inicjatora albo selfish duelist bez supportu dostają kary.
- **Profil użytkownika** - tryb początkujący i preferowany styl gry modyfikują wynik, ale nie powinny wygrywać z krytycznym brakiem roli.

Wynik końcowy jest wyjaśnialny: najlepszy pick i alternatywy mają listę powodów oraz ostrzeżeń, więc łatwo zobaczyć, czy rekomendacja wynika z mapy, brakującej roli, utility, synergii czy profilu gracza.

## Inspiracja techniczna

Nieoficjalna dokumentacja Valorant API opisuje m.in.:

- `GET /parties/v1/players/{puuid}` jako źródło aktualnego `CurrentPartyID`,
- `GET /pregame/v1/players/{puuid}` jako źródło `MatchID`,
- `GET /pregame/v1/matches/{matchId}` jako źródło `MapID`, `AllyTeam`, `CharacterSelectionState`, `QueueID`, `IsRanked`, `PhaseTimeRemainingNS` i `StepTimeRemainingNS`.

Repozytorium `valclient.py` jest traktowane tylko jako inspiracja dla separacji klienta API od logiki aplikacji.
