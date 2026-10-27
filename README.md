# Nightreign Relic Helper

App desktop per Windows che legge le reliquie dal salvataggio di Elden Ring Nightreign,
consiglia quali buttare e mostra tier list, armi e build per ogni personaggio.
Interfaccia e nomi in italiano o inglese (pulsanti IT/EN).

## Avvio

- **Eseguibile:** `dist\NightreignRelicHelper\NightreignRelicHelper.exe` (non serve Python).
  Si ricrea con `build.bat`.
- **Da sorgente:** doppio clic su `Avvia.bat` (al primo avvio prepara l'ambiente Python).

## Pagine

- **Reliquie**: tutto l'inventario, con ricerca e filtri.
- **Da buttare**: doppioni, reliquie superate da un'altra dello stesso colore, reliquie con punteggio basso.
  Con "Gioco in solitaria" gli effetti che aiutano solo gli alleati valgono 0.
- **Personaggi**: per ognuno dei 10 personaggi tier list degli effetti (normali e profondi), malus innocui
  e da evitare, passivi delle armi, armi migliori e build, con quante reliquie possiedi per ogni effetto.

## Come funziona

- Cerca i salvataggi in `%APPDATA%\Nightreign\<SteamID>\` (`.sl2` e `.co2`) e apre il più recente.
  Con le mod il file può avere un nome diverso (es. `N0000.sl2`): si sceglie dal menu in alto.
- Il salvataggio viene **solo letto**, mai modificato. Ogni 3 secondi controlla se è cambiato.
- Il server ascolta solo su `127.0.0.1` e si chiude da solo quando chiudi la finestra.

## Dati della ricerca e aggiornamento mensile

- `research/` contiene i voti degli effetti (`ratings.json`), le schede dei personaggi (`characters.json`)
  e data, novità e fonti (`meta.json`).
- Ogni mese una routine di Claude nel cloud rifà la ricerca seguendo `research/ROUTINE.md`,
  controlla i file con `tools/validate_research.py` e li pubblica su GitHub.
- All'avvio l'app scarica i dati più recenti dal repository (`REPO` in `app/paths.py`), li verifica e li salva
  in `%APPDATA%\NightreignRelicHelper\research`. Se sei offline usa quelli che ha.
- I tuoi voti personali vanno in `%APPDATA%\NightreignRelicHelper\my_ratings.json` (stesso formato di
  `ratings.json`, solo `effects` e/o `curses`): hanno la precedenza e non vengono mai sovrascritti.

## Struttura

- `app/save_reader.py`: decifra il salvataggio ed estrae le reliquie.
- `app/analysis.py`: punteggi e consigli su cosa buttare.
- `app/research.py`: caricamento e aggiornamento dei dati della ricerca.
- `app/main.py`: server locale e finestra. `app/ui/`: interfaccia.
- `data/`: tabelle ID → nomi del gioco, generate con `tools/build_data.py`.

## Aggiornare le tabelle del gioco dopo una patch

Se compaiono "Effetto sconosciuto" o "Reliquia sconosciuta":

```
python tools/build_data.py <cartella src/Resources del Nightreign Save Editor aggiornato>
```
