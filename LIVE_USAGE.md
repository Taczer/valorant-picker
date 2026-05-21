# Jak odpalić odczytywanie teamu i rekomendację picka

Ten tryb działa lokalnie na Twoim komputerze. Program czyta dane z lokalnego Riot Clienta i read-only endpointów Valoranta.

Program **nie wybiera agenta**, **nie lockuje agenta**, **nie klika w klienta gry** i **nie zapisuje tokenów na dysk**.

## 1. Otwórz terminal w folderze projektu

W PowerShellu przejdź do katalogu projektu:

```powershell
cd "D:\valo picker"
```

## 2. Sprawdź czy program działa

Uruchom demo bez Valoranta:

```powershell
python -m valo_picker --sample
```

Powinieneś zobaczyć ekran:

```text
PRE-GAME (AGENT SELECT)
Map: Ascent
Your Team:
Recommendation:
Best Pick: Omen
```

Jeśli to działa, Python i projekt są poprawnie uruchamiane.

## 3. Odpal Riot Client i Valoranta

Uruchom normalnie:

1. Riot Client,
2. Valorant,
3. wejdź do lobby,
4. rozpocznij kolejkę albo custom,
5. poczekaj aż wejdziesz w wybór agentów.

Program ma największy sens dopiero wtedy, gdy jesteś w fazie **Agent Select**.

## 4. Sprawdź status połączenia

W drugim oknie PowerShella uruchom:

```powershell
python -m valo_picker --status
```

Dobry znak:

```text
Valorant uruchomiony: tak
Lockfile Riot Client: znaleziono
Live status: WAITING_FOR_AGENT_SELECT
```

Jeśli jesteś już w wyborze agenta, może pojawić się:

```text
Live status: AGENT_SELECT
```

Jeśli jesteś już w meczu, powinno pojawić się:

```text
Live status: IN_GAME
```

Program nie pokazuje tokenów. PUUID jest maskowany.

### Debug log bez tokenów

Jeśli coś nie działa albo Riot API zwraca dziwny status, uruchom:

```powershell
python -m valo_picker --status --debug
```

Domyślnie plik powstaje tutaj:

```text
logs/valo_picker_debug.log
```

Log zawiera:

- endpoint,
- HTTP status,
- status programu, np. `AGENT_SELECT` albo `IN_GAME`,
- skrócony `MatchID` i `PartyID`,
- warnings/errors normalizera.

Log nie zawiera:

- access tokenów,
- entitlement tokenów,
- nagłówków `Authorization`,
- haseł z lockfile.

UUID w endpointach są maskowane, np.:

```text
/core-game/v1/matches/4e154c62...d6f6
```

## 5. Uruchom odczyt teamu i rekomendację

Gdy jesteś w Agent Select, uruchom:

```powershell
python -m valo_picker
```

Program powinien pokazać ekran podobny do:

```text
======================================================================
                       PRE-GAME (AGENT SELECT)
======================================================================
Map: Ascent
Mode: pre-game / agent-select
State: AGENT_SELECT
Region: eu / Shard: eu
PUUID: 1234...abcd
PartyID: 12345678...abcd
MatchID: 87654321...abcd
----------------------------------------------------------------------
Your Team:
[Jett        ] Gracz 1 (locked/Lvl ?)
[Reyna       ] Gracz 2 (selected/Lvl ?)
[Killjoy     ] Gracz 3 (locked/Lvl ?)
[Sova        ] Gracz 4 (locked/Lvl ?)
[brak wyboru ] Ty (brak wyboru/Lvl ?)
----------------------------------------------------------------------
Recommendation:
  Best Pick: Omen (Controller)
  Alternatives: Clove, Brimstone, Astra, Miks
  Team Score: 4.5/10 -> 9.2/10
  Fill Role: Controller
Problems:
  - Brak controllera / smoke'ów.
Advice:
  Graj blisko teamu, dawaj smoke'i...
```

## 6. Jak czytać wynik

Najważniejsze pola:

- `Map` - aktualna mapa z lobby.
- `State` - status programu.
- `Your Team` - sojusznicy i ich agenci.
- `selected` - agent zaznaczony, ale niezalockowany.
- `locked` - agent zalockowany.
- `brak wyboru` - gracz jeszcze nic nie wybrał.
- `Best Pick` - najlepszy agent według programu.
- `Alternatives` - inne sensowne opcje.
- `Team Score` - ocena teamu teraz i po Twoim picku.
- `Problems` - największe braki w kompozycji.
- `Advice` - krótka porada jak grać rekomendowanym agentem.

## 7. Menu

Na dole ekranu jest menu:

```text
1. Refresh Now
2. List all agents
3. Manual Mode
4. Settings
0. Exit
```

Najczęściej używane:

- `1` - odśwież teraz,
- `2` - pokaż listę agentów,
- `3` - przejdź do trybu ręcznego,
- `4` - ustaw częstotliwość odświeżania i domyślny tryb startu,
- `0` - wyjdź.

Program odświeża dane automatycznie co około 5 sekund. Możesz to zmienić w `4. Settings`.

Możesz też jednorazowo nadpisać częstotliwość z terminala:

```powershell
python -m valo_picker --refresh 5.0
```

Dozwolony zakres to 2.0-10.0 sekund.

Ustawienia zapisują się w profilu użytkownika Windows:

```text
%APPDATA%\ValoPicker\settings.json
```

Domyślny tryb startu może być:

- `Live` - standardowy ekran live,
- `Manual` - od razu tryb ręczny,
- `Status` - od razu status połączenia.

Jeśli ustawisz `Manual` albo `Status`, możesz jednorazowo wymusić ekran live:

```powershell
python -m valo_picker --live
```

## 8. Tryb ręczny jako fallback

Jeśli Riot API nie działa albo nie jesteś w Agent Select, możesz użyć trybu ręcznego:

```powershell
python -m valo_picker --manual
```

Wtedy sam wpisujesz:

- mapę,
- agentów teamu,
- czy są `selected` albo `locked`,
- swój styl gry.

## 9. Typowe statusy

### `NO_CLIENT`

Program nie widzi Valoranta albo lockfile.

Co zrobić:

1. odpal Riot Client,
2. odpal Valoranta,
3. uruchom ponownie:

```powershell
python -m valo_picker --status
```

### `WAITING_FOR_AGENT_SELECT`

Program działa, ale nie jesteś jeszcze w wyborze agenta.

Co zrobić:

1. wejdź do kolejki,
2. poczekaj na Agent Select,
3. zostaw program uruchomiony albo wybierz `1. Refresh Now`.

Jeśli widzisz komunikat podobny do:

```text
Pre-Game Player unavailable (HTTP 403)
```

to zwykle oznacza, że Riot API nie udostępnia jeszcze danych pre-game dla Twojego konta albo nie jesteś faktycznie w Agent Select. Program będzie dalej czekał i odświeżał dane.

### `AGENT_SELECT`

To jest oczekiwany status.

Program powinien widzieć:

- mapę,
- team,
- picki selected/locked,
- rekomendację.

### `IN_GAME`

Program widzi, że jesteś już w aktywnym meczu.

W tym stanie Valo Picker pokazuje status gry, `MatchID` i aktualny team w formacie:

```text
Your Team:
Nick#TAG (Agent)
Nick#TAG (Agent)
```

Program nie generuje picka w trakcie meczu, bo rekomendacje działają tylko w Agent Select. To jest normalne, jeśli wszyscy już zatwierdzili agentów i mecz się rozpoczął.

Jeśli program rozpozna Twojego agenta i mapę, pokaże też:

```text
Your Agent Advice:
  Krótka porada jak grać aktualną postacią na tej mapie.
```

### `ERROR`

Program połączył się z klientem, ale Riot API zwróciło błąd.

Co zrobić:

1. uruchom:

```powershell
python -m valo_picker --status
```

2. sprawdź komunikat,
3. jeśli komunikat dotyczy `Party Player`, program zwykle nadal spróbuje pobrać Pre-Game Match,
4. jeśli komunikat dotyczy `pregame` i nadal jesteś w Agent Select, wybierz `1. Refresh Now`, wejdź ponownie w lobby albo zrestartuj Valoranta.

## 10. Najważniejsze ograniczenie

Valo Picker tylko podpowiada.

Program nie ma funkcji:

- auto-pick,
- auto-lock,
- klikania w klienta gry,
- obchodzenia Vanguard,
- czytania pamięci gry.

Ty sam wybierasz agenta w Valorancie.

## 11. Jeśli polskie znaki dalej są jako `?`

Nowa wersja ustawia kodowanie klasycznego CMD na stronę OEM Windowsa. Jeśli nadal widzisz `Domy?lny` albo `Wyb?r`, problemem jest zwykle font okna konsoli.

Najprostsze obejście:

1. kliknij prawym na pasek tytułu okna CMD,
2. wybierz `Properties`,
3. przejdź do `Font`,
4. ustaw `Consolas` albo `Lucida Console` zamiast `Raster Fonts`,
5. uruchom `dist\ValoPicker.exe` ponownie.

Alternatywnie uruchom aplikację w Windows Terminal albo PowerShell.
