# Profil gracza w Valo Picker

Profil gracza mówi programowi, jaki typ picków ma lekko preferować przy rekomendacji agenta.

To nie jest twarda blokada. Jeśli team nie ma controllera, a mapa bardzo potrzebuje smoke'ów, program nadal będzie mocno promował controllera nawet wtedy, gdy wybierzesz agresywny styl gry.

## Jak wpisać styl

W trybie ręcznym program pokazuje:

```text
Profil gracza:
1. agresywny entry
2. spokojny support
3. lurker
4. smoker/controller
5. sentinel/defensywny
6. initiator/support
7. solo queue
8. początkujący
Style po przecinku, np. 4,7 albo puste:
```

Możesz wpisać jeden numer:

```text
4
```

Możesz wpisać kilka numerów po przecinku:

```text
4,7
```

Możesz też zostawić puste pole. Wtedy program rekomenduje tylko na podstawie mapy i teamu.

## Znaczenie stylów

### 1. Agresywny entry

Dla gracza, który chce otwierać rundę, brać pierwszy kontakt i robić miejsce teamowi.

Program lekko promuje agentów takich jak:

- Jett,
- Raze,
- Neon,
- Phoenix,
- Iso,
- Clove.

Ważne: jeśli team ma już dużo duelistów, program nie powinien polecać kolejnego duelista tylko dlatego, że wybrałeś agresywny styl.

### 2. Spokojny support

Dla gracza, który woli pomagać teamowi utility, trade'ować i grać bardziej metodycznie.

Program lekko promuje agentów takich jak:

- Omen,
- Brimstone,
- Sova,
- Skye,
- Gekko,
- Sage.

Ten styl pasuje, jeśli nie chcesz być pierwszą osobą wbiegającą na site.

### 3. Lurker

Dla gracza, który lubi grać wolniej, przejmować mapę, pilnować rotacji i karać przeciwników za przesunięcia.

Program lekko promuje agentów takich jak:

- Omen,
- Cypher,
- Chamber,
- Yoru.

Ważne: lurk nie ma sensu, jeśli team potrzebuje od Ciebie smoke'ów albo wejścia razem z drużyną. Program nadal bierze pod uwagę potrzeby teamu.

### 4. Smoker/controller

Dla gracza, który chce grać controllerem i pilnować smoke'ów.

Program lekko promuje agentów takich jak:

- Omen,
- Brimstone,
- Astra,
- Viper,
- Harbor,
- Clove.

To bardzo dobry wybór profilu, jeśli często grasz solo queue i chcesz uzupełniać najważniejszy brak w teamie.

### 5. Sentinel/defensywny

Dla gracza, który lubi trzymać site, pilnować flanki i grać cierpliwie.

Program lekko promuje agentów takich jak:

- Killjoy,
- Cypher,
- Sage,
- Chamber,
- Deadlock,
- Vyse.

Ten styl jest dobry, jeśli chcesz dawać teamowi bezpieczeństwo i informacje zamiast grać pierwszy kontakt.

### 6. Initiator/support

Dla gracza, który lubi dawać info, flashować pod wejście i pomagać duelistom.

Program lekko promuje agentów takich jak:

- Sova,
- Fade,
- Skye,
- Gekko,
- Breach,
- KAY/O,
- Tejo.

Ten styl pasuje, jeśli chcesz grać blisko teamu i ustawiać utility pod execute albo retake.

### 7. Solo queue

Dla gracza, który gra sam i chce agentów elastycznych, mniej zależnych od pełnej komunikacji.

Program lekko promuje agentów, którzy dobrze działają bez idealnej koordynacji, np.:

- Omen,
- Clove,
- Phoenix,
- Reyna,
- Killjoy,
- Cypher,
- Sova,
- Gekko.

To nie znaczy, że program zawsze poleci samowystarczalnego agenta. Jeśli team nie ma smoke'ów, controller nadal będzie priorytetem.

### 8. Początkujący

Dla gracza, który chce prostszych agentów i mniej skomplikowanego utility.

Program lekko promuje łatwiejszych agentów, np.:

- Brimstone,
- Sage,
- Phoenix,
- Gekko,
- Reyna.

Program może też mniej chętnie polecać bardzo trudnych agentów, jeśli istnieje prostsza alternatywa pasująca do teamu.

## Przykładowe wpisy

### Chcę grać smoke'i i gram solo

```text
4,7
```

Program będzie lubił controllerów dobrych w solo queue, np. Omen albo Clove.

### Jestem początkujący i chcę grać support

```text
2,8
```

Program będzie częściej wybierał prostszych agentów wspierających team.

### Lubię grać spokojnie i defensywnie

```text
2,5
```

Program będzie częściej promował sentinelów albo support utility.

### Chcę grać agresywnie, ale niekoniecznie duelista

```text
1,7
```

Program może polecić duelista, ale może też polecić agresywnego controllera, np. Clove, jeśli team potrzebuje smoke'ów.

## Jak profil wpływa na rekomendację

Profil daje bonus do agentów pasujących do Twojego stylu, ale nie wygrywa z najważniejszymi potrzebami teamu.

Priorytety programu są mniej więcej takie:

1. Czy agent jest dostępny.
2. Czy team ma controllera i smoke'i.
3. Czy team ma inicjatora, sentinela i entry.
4. Czy agent pasuje do mapy.
5. Czy agent uzupełnia brakujące utility.
6. Czy agent pasuje do Twojego profilu.

Dlatego profil pomaga dopasować pick do Ciebie, ale program nadal pilnuje sensownej kompozycji teamu.

