# Valo Picker - notatki meta map i agentów

Aktualizacja robocza: 2026-05-18.

Ten plik opisuje, jak MVP ocenia agentów na mapach. To nie jest prawda absolutna ani cheat sheet pro-play. To lokalny, praktyczny model do ranked/solo queue, który łączy:

- role w teamie,
- utility potrzebne na mapie,
- rekomendowanych agentów per rola,
- prostotę gry,
- solo queue,
- synergie typu `Jett + Sova` albo `Raze + Fade`.

## Źródła użyte do strojenia

- OP.GG Help Center - opisuje map-specific statystyki agentów według pick rate i win rate:
  https://help.op.gg/hc/en-us/articles/48466781419161-How-to-check-recommended-agents-by-map
- MetaBot.GG - bieżące pick rate / win rate agentów i role:
  https://metabot.gg/en/valorant/agents/pick-rate
- Gamer.org 2026 map agent tier list:
  https://www.gamer.org/valorant-map-agent-tier-list-best-picks-for-every-map-in-2026/
- Gamer.org 2025 per-map tier list:
  https://www.gamer.org/valorant-agent-tier-list-best-agents-for-every-map-in-2025/
- Switchblade Gaming 2026 agent tier list:
  https://www.switchbladegaming.com/valorant/agent-tier-list/
- Valorant Tracker - przykład działania asystenta agent select i filtrowania pod mapę/rolę:
  https://tracker.gg/valorant/articles/valorant-in-game-agent-selection-assistant

## Zasada główna

Program najpierw pilnuje minimalnego szkieletu kompozycji:

- 1 Controller,
- 1 Initiator,
- 1 Sentinel,
- 1 Duelist/entry.

Jeśli team nie ma controllera, smoke'i mają najwyższy priorytet.

Jeśli team ma już smoke'i, info/flasha i flank watch, ale nie ma Duelista, program ma polecać Duelista. To jest ważne, bo bez entry team często stoi przed wejściem i nie bierze przestrzeni.

## Duelist - kiedy program ma go polecać

Program podbija Duelista, gdy:

- team ma 0 duelistów,
- są już smoke'i albo controller,
- jest initiator z info/flashem/stunem/clearem,
- mapa lubi szybkie wejście, mobilność albo czyszczenie kątów.

Program karze Duelista, gdy:

- to byłby trzeci Duelist,
- team nie ma smoke'ów,
- team nie ma initiatora,
- agent jest już selected/locked.

## Mapowe priorytety duelistów w MVP

- Ascent: Jett, Raze, Phoenix, Reyna.
- Bind: Raze, Yoru, Iso, Reyna, Phoenix.
- Breeze: Jett, Neon, Yoru.
- Fracture: Raze, Neon, Jett.
- Haven: Jett, Neon, Yoru, Phoenix, Waylay.
- Icebox: Jett, Yoru, Waylay, Reyna.
- Lotus: Raze, Neon, Waylay, Jett.
- Pearl: Yoru, Jett, Neon, Iso, Phoenix.
- Split: Raze, Yoru, Waylay, Jett, Neon.
- Sunset: Raze, Phoenix, Waylay, Iso, Neon.
- Abyss: Jett, Yoru, Neon.
- Corrode: Waylay, Raze, Jett, Phoenix, Iso.

## Dlaczego konkretni agenci

### Jett

Dobra na mapach z długimi liniami, wertykalnością albo wartością Operatora: Ascent, Breeze, Icebox, Haven, Abyss. Daje pierwszy kontakt i może się wycofać po dashu.

### Raze

Dobra na mapach ciasnych, z wieloma bliskimi kątami: Bind, Lotus, Split, Fracture, Sunset. Granat i satchele pomagają czyścić kąty, gdzie suchy entry ginie bez value.

### Neon

Dobra, gdy mapa lub kompozycja potrzebuje tempa: Lotus, Fracture, Haven, Breeze. Wymaga pewności w movement/aim, ale mocno przyspiesza przejmowanie przestrzeni.

### Yoru

Dobra na mapach, gdzie teleport i flash mogą zmieniać tempo albo wymuszać rotacje: Bind, Pearl, Breeze, Haven, Split. Trudniejszy, ale może dać wysokie value.

### Phoenix

Dobry jako prostszy Duelist do solo queue lub początkującego stylu. Daje flash i self sustain, ale nie zawsze otwiera przestrzeń tak mocno jak Jett/Raze/Neon.

### Reyna / Iso

Dobre, gdy gracz chce brać pojedynki w solo queue. Program nie powinien ich wciskać jako domyślne entry, jeśli team potrzebuje więcej utility lub prawdziwego otwierania site'u.

## Gdzie jest ta logika w kodzie

- Baza map: `valo_picker/data/maps.py`
- Baza agentów: `valo_picker/data/agents.py`
- Cechy map, synergie, powody i pro tipy agent+mapa: `valo_picker/strategy.py`
- Scoring kandydatów: `valo_picker/recommender.py`
- Testy scenariuszy: `tests/test_recommender.py`

## Pro tipy agent+mapa

W `MAP_AGENT_TIPS` są krótkie wskazówki używane w:

- `Advice` podczas rekomendacji picka,
- `Your Agent Advice` podczas aktywnego meczu.

Format porad jest praktyczny:

- co robić w ataku,
- co robić w obronie,
- czego unikać, żeby nie tracić value.
