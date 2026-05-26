from __future__ import annotations

from collections.abc import Mapping


LocalizedText = dict[str, str]
LocalizedTips = dict[str, tuple[str, ...]]
PairSynergy = tuple[float, LocalizedText, tuple[str, ...]]


_MAP_AGENT_NOTES_PL: dict[str, dict[str, str]] = {
    "Ascent": {
        "Jett": "Ascent nagradza mobilne entry i Operatora na midzie; Jett dobrze gra po reconie Sovy i smoke'ach Omena.",
        "Omen": "Omen odcina Heaven, Tree, Market i daje paranoję pod wejście przez ciasne chokepointy.",
        "Sova": "Sova daje stabilny recon na mid, A Main i B Main, więc team mniej ryzykuje suche wejścia.",
        "Killjoy": "Killjoy zabezpiecza flankę i wzmacnia post-plant na klasycznych plant spotach.",
    },
    "Bind": {
        "Raze": "Bind ma krótkie wejścia i dużo bliskich kątów, więc granat i satchele Raze mają wysoką wartość.",
        "Brimstone": "Brimstone szybko zamyka Hookah, Lamps i CT, co pasuje do krótkich execute'ów na Bindzie.",
        "Fade": "Fade dobrze czyści Hookah, Lamps i U-Hall, gdzie sama informacja często decyduje wejście.",
        "Yoru": "Yoru może wykorzystywać teleportery i flashować ciasne wejścia bez oddawania tempa.",
    },
    "Breeze": {
        "Jett": "Breeze ma długie linie i wartość Operatora, więc Jett daje presję pierwszego kontaktu i bezpieczny reset.",
        "Viper": "Viper jest kluczowa na długich liniach, bo wall odcina kilka kątów naraz i pomaga bezpiecznie plantować.",
        "Sova": "Sova dobrze skanuje szerokie przestrzenie, gdzie zwykły flash często nie wystarcza.",
        "Cypher": "Cypher pilnuje długich flank i daje pasywne info na mapie z dużą przestrzenią.",
    },
    "Fracture": {
        "Raze": "Fracture premiuje szybkie wejścia z dwóch stron; Raze czyści bliskie kąty i tworzy przestrzeń satchelami.",
        "Breach": "Breach jest bardzo mocny na Fracture, bo stun i flash pokrywają długie, przewidywalne wejścia.",
        "Brimstone": "Brimstone daje szybkie smoke'i pod split execute i mocny post-plant.",
        "Neon": "Neon dobrze wykorzystuje tempo mapy i szybkie przejęcie przestrzeni przy pinch atakach.",
    },
    "Haven": {
        "Jett": "Haven ma długie linie i trzy site'y, więc Jett może brać pierwszy kontakt i szybko resetować po dashu.",
        "Sova": "Sova zbiera informację na A, C i midzie bez wymuszania ryzykownych peeków.",
        "Cypher": "Cypher stabilizuje B, Garage i flankę, co jest ważne przy trzech site'ach.",
        "Omen": "Omen dobrze obsługuje rotacje i smoke'i na wielu wejściach Haven.",
    },
    "Icebox": {
        "Jett": "Icebox ma wertykalne pozycje i długie kąty, więc Jett najlepiej wykorzystuje dash, updraft i Operatora.",
        "Viper": "Viper daje ścianę pod plant i post-plant, czyli najważniejszą wartość controllera na Icebox.",
        "Sova": "Sova dobrze czyta wertykalne site'y i ułatwia wejście na plant.",
        "Sage": "Sage upraszcza plant i retake przez wall oraz slow orby.",
    },
    "Lotus": {
        "Raze": "Lotus ma ciasne wejścia i szybkie rotacje, więc Raze bardzo dobrze czyści kąty i otwiera site.",
        "Fade": "Fade wspiera szybkie wejścia przez prowlera i haunt na ciasnych przestrzeniach.",
        "Omen": "Omen dobrze obsługuje trzy site'y i krótkie smoke'i pod wejście oraz retake.",
        "Neon": "Neon korzysta z tempa Lotus i może szybko karać rotacje między site'ami.",
    },
    "Pearl": {
        "Yoru": "Pearl daje dużo przestrzeni na mind game, flash i zmianę tempa przez teleporty.",
        "Astra": "Astra kontroluje mid i długie B z dużej odległości, co pasuje do szerokiego układu mapy.",
        "Fade": "Fade daje info na close-corner walkach i wspiera wejścia przez prowlera.",
        "Jett": "Jett daje presję na długich liniach i może bezpiecznie brać pierwszy kontakt.",
    },
    "Split": {
        "Raze": "Split ma ciasne wejścia i dużo bliskich kątów, więc Raze wnosi najwięcej entry i clearu.",
        "Breach": "Breach wzmacnia wejścia przez stun i flash na ciasnych chokepointach.",
        "Omen": "Omen dobrze walczy o mid i odcina Heaven na obu site'ach.",
        "Cypher": "Cypher stabilizuje flankę i kontrolę mida, gdy team rotuje przez wąskie przejścia.",
    },
    "Sunset": {
        "Raze": "Sunset premiuje clear bliskich pozycji na B Main i midzie, dlatego Raze dobrze otwiera przestrzeń.",
        "Omen": "Omen daje elastyczne smoke'i na mid, A Main i B Main oraz flash pod wejście.",
        "Cypher": "Cypher mocno pilnuje flank i B Main, gdzie pasywne info ma dużą wartość.",
        "Fade": "Fade czyści bliskie kąty i daje info pod wejścia przez mida.",
    },
    "Abyss": {
        "Jett": "Abyss ma duże przestrzenie i długie kąty, więc Jett wykorzystuje Operatora i mobilne pierwsze kontakty.",
        "Astra": "Astra dobrze kontroluje szerokie przestrzenie i odległe chokepointy.",
        "Sova": "Sova daje bezpieczne info na otwartych liniach, gdzie facecheck jest kosztowny.",
        "Cypher": "Cypher ogranicza lurki i flankę na mapie z dużą przestrzenią.",
    },
    "Corrode": {
        "Waylay": "Corrode w modelu MVP premiuje szybkie przejęcie przestrzeni; Waylay pasuje jako mobilny entry.",
        "Omen": "Omen jest elastycznym domyślnym controllerem, gdy mapa wymaga smoke'ów i walki o mid.",
        "Fade": "Fade daje info i clear na wejściach, zanim team odda pierwszy kontakt.",
        "Raze": "Raze pomaga czyścić ciasne kąty i utrzymać tempo execute'u.",
    },
}


_MAP_AGENT_TIPS_PL: dict[str, dict[str, tuple[str, ...]]] = {
    "Ascent": {
        "Jett": (
            "Atak: proś o recon/flash przed dashem, potem dashuj za smoke na site, nie na suchy kontakt.",
            "Obrona: pilnuj mida albo A Main z możliwością szybkiego resetu po pierwszym strzale.",
            "Nie lurkuj długo, jeśli team nie ma innego entry.",
        ),
        "Omen": (
            "Atak: smoke Heaven/Tree/Market przed wejściem i trzymaj drugi smoke na rotację albo retake przeciwnika.",
            "Paranoia jest najlepsza pod wejście Jett/Raze przez A Main, B Main albo mid.",
            "Nie oddawaj życia przed execute, bo team traci wszystkie smoke'i.",
        ),
        "Sova": (
            "Atak: zaczynaj rundy od reconu pod A Main/B Main albo mid, żeby entry nie wchodził w ciemno.",
            "Shocki i drone zostawiaj na clear bliskich pozycji oraz post-plant.",
            "Obrona: nie używaj całego info od razu, jeden recon zachowaj pod retake.",
        ),
        "Killjoy": (
            "Atak: turret/alarmbot mają pilnować flanki, żeby reszta mogła grać execute.",
            "Obrona: graj pod kontakt utility i cofaj się po value zamiast umierać na pierwszym peeku.",
            "Lockdown trzymaj na retake A/B albo pewne domknięcie post-planta.",
        ),
    },
    "Bind": {
        "Raze": (
            "Atak: używaj boombota/granatu do czyszczenia Hookah, Lamps i bliskich kątów przed wejściem.",
            "Satchele mają brać przestrzeń po flashu albo smoke'u, nie solo przez smoke przeciwnika.",
            "Obrona: granat trzymaj na zatrzymanie szybkiego wejścia pod Hookah albo Short.",
        ),
        "Brimstone": (
            "Atak: dawaj szybkie smoke'i na CT, Heaven/Lamps i izoluj site przed wejściem.",
            "Stim ma iść razem z wejściem teamu, nie po fakcie.",
            "Molly zachowuj pod post-plant albo zatrzymanie defuse'a.",
        ),
        "Fade": (
            "Atak: prowlerem czyść Hookah/Lamps, a haunt rzucaj tak, żeby wymusić odwrócenie celowników.",
            "Ult najlepiej łączyć z szybkim wejściem Raze albo teleportem rotacyjnym.",
            "Obrona: nie facecheckuj teleportów, najpierw daj info.",
        ),
        "Yoru": (
            "Atak: fake teleport i flash zmuszają rotacje, ale prawdziwe wejście rób dopiero z teamem.",
            "Na Bindzie teleportery są narzędziem tempa, nie zaproszeniem do samotnego lurka co rundę.",
            "Flashuj ciasne wejścia nisko/od ściany, żeby nie oślepiać własnego entry.",
        ),
    },
    "Breeze": {
        "Jett": (
            "Atak: bierz pierwszy kontakt na długich liniach, ale resetuj dashem po strzale albo po wejściu za smoke.",
            "Operator ma dużą wartość, szczególnie przy kontroli mida i długich podejść.",
            "Nie dashuj głęboko bez info, bo Breeze karze brak trade'a na szerokiej przestrzeni.",
        ),
        "Viper": (
            "Atak: wall ma odciąć kilka długich linii naraz i umożliwić bezpieczny plant.",
            "Nie zużywaj toksyny na puste sekundy; aktywuj ją, gdy team faktycznie bierze przestrzeń.",
            "Molly zachowuj pod post-plant albo opóźnienie retake'u.",
        ),
        "Sova": (
            "Atak: recon ma sprawdzić szerokie przestrzenie przed wejściem, bo zwykły flash często nie pokrywa wszystkich kątów.",
            "Drone jest mocny do wejścia na site, ale team musi iść za nim od razu.",
            "Obrona: graj info pod retake zamiast walczyć solo na długich liniach.",
        ),
        "Skye": (
            "Atak: pies ma czyścić bliskie kąty, a flash ma potwierdzać kontakt na szerokich wejściach.",
            "Heal jest wartościowy na Breeze, bo długie walki często kończą się dużym chip damage.",
            "Nie flashuj zbyt wysoko na otwartych przestrzeniach, bo przeciwnik łatwo ją odwróci.",
        ),
        "Chamber": (
            "Obrona: ustaw teleport tak, żeby brać pierwszy kontakt na długiej linii i bezpiecznie wyjść.",
            "Trip ma zabezpieczać flankę, nie dekorować miejsca, którego nikt nie wykorzystuje.",
            "Nie próbuj zastępować Cyphera/Killjoya pełnym site anchorem; graj pick i reset.",
        ),
    },
    "Fracture": {
        "Raze": (
            "Atak: satchel entry działa najlepiej, gdy drugi koniec mapy też robi presję.",
            "Granat zachowuj na bliskie kąty i anti-rush, bo mapa ma dużo szybkich timingów.",
            "Nie wchodź samotnie z jednej strony, jeśli team nie robi pinch.",
        ),
        "Breach": (
            "Atak: stun i flash ustawiaj pod wejście z dwóch stron, żeby przeciwnik nie miał bezpiecznego kąta.",
            "Obrona: utility najlepiej opóźnia szybkie wejścia, więc nie spalaj wszystkiego na fake.",
            "Ult jest bardzo mocny pod retake lub szybki split execute.",
        ),
    },
    "Haven": {
        "Jett": (
            "Atak: wykorzystuj dash do przejęcia przestrzeni na A Long, C Long albo przez Garage po utility.",
            "Obrona: zmieniaj pozycje, bo trzy site'y karzą przewidywalne granie Operatora.",
            "Nie zostawiaj teamu bez entry na execute, jeśli jesteś jedynym duelistą.",
        ),
        "Omen": (
            "Smoke'i rozkładaj pod tempo rundy: jeden na wejście, drugi na rotację albo retake.",
            "Paranoia przez Garage lub krótkie wejścia daje więcej value niż samotny lurk.",
            "Na trzech site'ach żywy controller jest ważniejszy niż ryzykowny pierwszy duel.",
        ),
        "Sova": (
            "Recon rotacyjny jest bardzo mocny, bo Haven ma trzy site'y i dużo fake'ów.",
            "Drone pod C Long/Garage pomaga entry wchodzić bez facechecka.",
            "Zachowaj jedno info pod late round, gdy przeciwnik zmieni site.",
        ),
    },
    "Icebox": {
        "Jett": (
            "Atak: dash/updraft pozwala wejść na wertykalne pozycje, ale potrzebujesz smoke'a albo info przed skokiem.",
            "Operator działa dobrze na długich kątach, ale po pierwszym kontakcie zmieniaj pozycję.",
            "Nie graj tylko lurka, jeśli team potrzebuje przestrzeni pod plant.",
        ),
        "Viper": (
            "Wall pod plant jest priorytetem; bez niego team często ginie podczas samego sadzenia spike'a.",
            "Toksynę włączaj w momencie wejścia albo retake'u, nie za wcześnie.",
            "Molly i orb są mocne do post-planta, ale nie oddawaj site'u bez żadnego spowolnienia.",
        ),
        "Sage": (
            "Wall ma ułatwić plant albo odciąć retake, nie musi być zawsze tym samym schematem.",
            "Slow orby rzucaj na wejścia retake'u albo pod zatrzymanie szybkiego pusha.",
            "Nie stój z healem w ręku, gdy team potrzebuje trade'a.",
        ),
    },
    "Lotus": {
        "Raze": (
            "Atak: boombot i granat są świetne do czyszczenia ciasnych wejść oraz zakrętów przy drzwiach.",
            "Satchel entry rób po smoke'u/flashu, bo Lotus szybko karze samotne wejścia.",
            "Obrona: utrzymuj granat na szybkie pushe przez chokepointy.",
        ),
        "Fade": (
            "Prowler ma prowadzić wejście przez ciasne przestrzenie, a nie iść bez teamu.",
            "Haunt używaj pod kontakt na site lub retake, gdzie przeciwnik ma mało miejsca na ucieczkę.",
            "Ult łącz z wejściem Raze/Neon albo szybkim retake.",
        ),
        "Omen": (
            "Trzy site'y wymagają elastycznych smoke'ów; nie zużywaj obu na pierwszy fake.",
            "Paranoia jest mocna przez ciasne wejścia i obrotowe drzwi.",
            "Graj blisko teamu, jeśli jesteś jedynym controllerem.",
        ),
    },
    "Split": {
        "Raze": (
            "Atak: czyść bliskie kąty boombotem/granatem, szczególnie przy wejściach na site i walce o mid.",
            "Satchele mają przełamać ciasny chokepoint po flashu/stunie.",
            "Obrona: granat jest mocny na zatrzymanie szybkiego wejścia, więc nie wyrzucaj go bez info.",
        ),
        "Omen": (
            "Smoke Heaven i kontrola mida są ważniejsze niż losowe agresywne teleporty.",
            "Paranoia przez wąskie przejścia daje duże value pod wejście albo retake.",
            "Zachowaj smoke na retake, jeśli team oddaje site.",
        ),
        "Breach": (
            "Stun i flash przez ciasne ściany mają przygotować entry, nie tylko zdobyć pojedynczy duel.",
            "Ult świetnie działa pod retake albo szybkie przejęcie mida.",
            "Nie używaj całego utility bez informacji, bo Split ma dużo fake presji.",
        ),
    },
    "Sunset": {
        "Raze": (
            "Atak: clear B Main i mida ma dużą wartość, bo przeciwnik często gra blisko.",
            "Satchel entry najlepiej działa po smoke'u na kluczowe kąty i flashu/init utility.",
            "Obrona: granat trzymaj na zatrzymanie wejścia przez ciasny chokepoint.",
        ),
        "Omen": (
            "Smoke'i na mid i mainy ustawiaj pod konkretny timing wejścia, nie na autopilocie.",
            "Paranoia jest mocna pod B Main i walkę o mid.",
            "Nie gin przed execute, bo Sunset bardzo potrzebuje smoke'ów w late round.",
        ),
        "Cypher": (
            "Trip i kamera mają kontrolować flankę lub B Main, żeby team mógł skupić się na execute.",
            "Nie pokazuj tych samych setupów co rundę, bo utility szybko traci value.",
            "W ataku graj pod info i late lurk, ale nie opuszczaj teamu, jeśli brakuje kontroli mapy.",
        ),
    },
    "Abyss": {
        "Jett": (
            "Atak: używaj mobilności do bezpiecznego pierwszego kontaktu na długich kątach.",
            "Operator i szybki reset mają dużą wartość, ale potrzebujesz info, żeby nie wejść w crossfire.",
            "Uważaj na zbyt głębokie dashe bez trade'a, bo mapa ma dużo otwartej przestrzeni.",
        ),
        "Astra": (
            "Gwiazdy ustawiaj pod kontrolę szerokich wejść i opóźnienie retake'u.",
            "Nie zużywaj całego utility na pierwszy kontakt; Abyss często gra się przez rotacje.",
            "Gravity well i stun łącz z reconem albo pierwszym kontaktem duelista.",
        ),
        "Cypher": (
            "Setup ma ograniczać lurki i flankę, bo mapa daje dużo przestrzeni do obejścia.",
            "Kamera powinna dawać info bez ryzykownego peekowania długich linii.",
            "Nie graj zbyt daleko od utility, jeśli jesteś jedynym sentinel.",
        ),
    },
}


_PAIR_SYNERGIES_PL: dict[frozenset[str], tuple[float, str, tuple[str, ...]]] = {
    frozenset({"Jett", "Sova"}): (7.0, "Jett + Sova dobrze łączą entry z reconem na otwartych liniach.", ("Ascent", "Breeze", "Haven", "Pearl", "Icebox")),
    frozenset({"Jett", "KAY/O"}): (6.0, "Jett + KAY/O dają szybkie wejście po suppressie albo flashu.", ("Ascent", "Breeze", "Icebox")),
    frozenset({"Raze", "Fade"}): (8.0, "Raze + Fade mocno czyści ciasne pozycje przez seize/prowler i granat.", ("Bind", "Lotus", "Split", "Sunset")),
    frozenset({"Raze", "Breach"}): (7.0, "Raze + Breach tworzą bardzo mocny kontakt na ciasnych wejściach.", ("Fracture", "Split", "Lotus")),
    frozenset({"Viper", "Harbor"}): (9.0, "Podwójna ściana daje stabilny plant i odcina długie linie.", ("Breeze", "Icebox", "Pearl", "Abyss")),
    frozenset({"Killjoy", "Sova"}): (5.0, "Killjoy + Sova wzmacniają info, retake i post-plant.", ("Ascent", "Haven", "Icebox", "Pearl")),
    frozenset({"Omen", "Breach"}): (5.0, "Omen + Breach dobrze grają pod flash/stun i wejście przez chokepoint.", ("Haven", "Split", "Lotus")),
    frozenset({"Gekko", "Viper"}): (5.0, "Gekko + Viper pomagają bezpiecznie plantować i grać post-plant.", ("Icebox", "Bind", "Pearl")),
}



def _localized_note(map_name: str, agent_name: str, polish_text: str) -> LocalizedText:
    return {
        "pl": polish_text,
        "en": f"{agent_name} has a map-specific fit on {map_name} and adds useful role value for this composition.",
    }


def _localized_tips(map_name: str, agent_name: str, polish_tips: tuple[str, ...]) -> LocalizedTips:
    return {
        "pl": polish_tips,
        "en": (
            f"Attack: use {agent_name}'s key utility with the team timing on {map_name}, not as a disconnected solo play.",
            f"Defense: hold the space where {agent_name}'s utility gives early value, then reposition before being traded.",
            "Keep one useful tool for retake or late round pressure instead of spending the full kit at the start.",
        ),
    }


def _localized_pair(pair: frozenset[str], polish_text: str) -> LocalizedText:
    names = sorted(pair)
    return {
        "pl": polish_text,
        "en": f"{names[0]} + {names[1]} create useful synergy for map control, entry setup or post-plant value.",
    }


MAP_AGENT_NOTES: dict[str, dict[str, LocalizedText]] = {
    map_name: {
        agent_name: _localized_note(map_name, agent_name, polish_text)
        for agent_name, polish_text in agent_notes.items()
    }
    for map_name, agent_notes in _MAP_AGENT_NOTES_PL.items()
}


MAP_AGENT_TIPS: dict[str, dict[str, LocalizedTips]] = {
    map_name: {
        agent_name: _localized_tips(map_name, agent_name, polish_tips)
        for agent_name, polish_tips in agent_tips.items()
    }
    for map_name, agent_tips in _MAP_AGENT_TIPS_PL.items()
}


PAIR_SYNERGIES: dict[frozenset[str], PairSynergy] = {
    pair: (score, _localized_pair(pair, polish_text), maps)
    for pair, (score, polish_text, maps) in _PAIR_SYNERGIES_PL.items()
}


def localized_strategy_text(value: Mapping[str, str], language: str) -> str | None:
    if language in value:
        return value[language]
    return value.get("en")


def localized_strategy_tips(value: Mapping[str, tuple[str, ...]], language: str) -> tuple[str, ...]:
    if language in value:
        return value[language]
    return value.get("en", ())

