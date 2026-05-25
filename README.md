# Valo Picker

Valo Picker is a small local assistant for Valorant Agent Select.

Start `ValoPicker.exe`, then launch Valorant normally. When you enter Agent Select, the app reads your current team and map, then suggests what agent to pick, shows alternatives, and explains the main reason.

The player always makes the final decision. Valo Picker does not pick, lock, click, inject, read game memory, bypass Vanguard, or save Riot tokens.

Repository: [Taczer/valorant-picker](https://github.com/Taczer/valorant-picker)

## Download

Download the latest Windows build from:

[GitHub Releases](https://github.com/Taczer/valorant-picker/releases)

Run:

```powershell
.\ValoPicker.exe
```

That is the normal mode. Keep the window open while you play.

## What It Shows

- recommended agent
- alternative picks
- missing team roles, for example no smokes
- short map/team reason
- optional player profile preference

## Useful Options

```powershell
.\ValoPicker.exe --manual
.\ValoPicker.exe --sample
.\ValoPicker.exe --status
.\ValoPicker.exe --status --debug
```

Settings are saved locally in:

```text
%APPDATA%\ValoPicker\settings.json
```

## Safety

Valo Picker is read-only.

It does not:

- auto-pick or auto-lock agents
- control the Valorant window
- read or modify game memory
- store Riot auth tokens
- bypass Vanguard

This is an unofficial fan-made tool and is not endorsed by Riot Games. Valorant is a trademark of Riot Games.

## Documentation

- [Profile Guide](PROFILE_GUIDE.md)
- [Live Usage](LIVE_USAGE.md)
- [Build EXE](BUILD_EXE.md)
- [Changelog](CHANGELOG.md)

---

## Polski

Valo Picker to mały lokalny asystent do Agent Select w Valorancie.

Odpalasz `ValoPicker.exe`, potem normalnie uruchamiasz Valoranta. Gdy wejdziesz w Agent Select, program odczyta mapę i aktualny skład teamu, a następnie pokaże, jakiego agenta warto wybrać, jakie są alternatywy i dlaczego.

Program nie wybiera i nie lockuje agentów. Nie klika w grę, nie czyta pamięci gry, nie omija Vanguard i nie zapisuje tokenów Riot.

### Pobieranie

[GitHub Releases](https://github.com/Taczer/valorant-picker/releases)

### Uruchomienie

```powershell
.\ValoPicker.exe
```

Zostaw okno programu otwarte podczas gry.

### Przydatne opcje

```powershell
.\ValoPicker.exe --manual
.\ValoPicker.exe --sample
.\ValoPicker.exe --status
.\ValoPicker.exe --status --debug
```
