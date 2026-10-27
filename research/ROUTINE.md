# Ricerca mensile: istruzioni per la routine

Questo file descrive cosa deve fare l'agente pianificato ogni mese. L'app scarica i file di questa
cartella (`meta.json`, `ratings.json`, `characters.json`) dal ramo `main`, quindi un commit sbagliato
arriva subito agli utenti: segui tutti i passi e **non fare commit se la validazione fallisce**.

## 1. Ricerca

Fai una ricerca web approfondita sul meta attuale di **Elden Ring Nightreign**, incluse modalità
"Deep of Night" (reliquie profonde) e DLC "The Forsaken Hollows" (Erudito/Scholar, Becchina/Undertaker).
L'utente gioca **in solitaria e offline**: valuta tutto in quell'ottica.

Fonti da coprire (lancia molte ricerche in parallelo, incrocia le fonti, segnala i disaccordi):
- patch notes ufficiali recenti (cosa è cambiato dall'ultima `meta.json` → `updated`);
- wiki (Fextralife, wiki.gg), Game8, GameRant, PCGamesN e altre guide;
- Reddit (r/Nightreign e simili), guide Steam;
- video YouTube, Shorts e TikTok tramite titoli, descrizioni e trascrizioni quando la pagina le espone.

Per **ognuno dei 10 personaggi** (Wylder, Guardian, Ironeye, Duchess, Raider, Revenant, Recluse,
Executor, Scholar, Undertaker):
1. effetti delle reliquie normali migliori, in tier S/A/B/C, con motivo;
2. effetti delle reliquie profonde migliori e malus innocui / da evitare;
3. effetti passivi delle armi migliori, in tier;
4. armi e tipi di arma migliori, in tier, con motivo;
5. 1-3 build consigliate (3 effetti normali + 3 profondi, calice consigliato).

Più in generale: effetti inutili in solitaria, regole di cumulabilità.

## 2. File da aggiornare

Usa **esattamente** i nomi inglesi degli effetti presenti in `data/effects.json` (campo `name_en`).
Se il gioco ha avuto una patch che aggiunge effetti o reliquie, rigenera prima le tabelle:
clona `https://github.com/alfizari/Elden-Ring-Nightreign-Save-Editor` e lancia
`python tools/build_data.py <clone>/src/Resources`.

### `characters.json`

```json
{
  "characters": {
    "Wylder": {
      "confidence": "high | medium | low",
      "summary": {"it": "...", "en": "..."},
      "relic_effects": [{"tier": "S", "effect": "<name_en esatto>", "why": {"it": "...", "en": "..."}}],
      "deep_effects":  [{"tier": "A", "effect": "<name_en esatto>", "why": {"it": "...", "en": "..."}}],
      "curses": {
        "harmless": [{"curse": "<name_en esatto>", "why": {"it": "...", "en": "..."}}],
        "avoid":    [{"curse": "<name_en esatto>", "why": {"it": "...", "en": "..."}}]
      },
      "weapon_passives": [{"tier": "S", "passive": {"it": "...", "en": "..."}, "why": {"it": "...", "en": "..."}}],
      "weapons": [{"tier": "S", "name": {"it": "...", "en": "..."}, "why": {"it": "...", "en": "..."}}],
      "builds": [{
        "name": {"it": "...", "en": "..."},
        "vessel": {"it": "...", "en": "..."},
        "normal": ["<name_en>", "<name_en>", "<name_en>"],
        "deep": ["<name_en>", "<name_en>", "<name_en>"],
        "notes": {"it": "...", "en": "..."}
      }]
    }
  },
  "general": {
    "solo_useless": ["<name_en>"],
    "stacking": [{"it": "...", "en": "..."}]
  }
}
```

I testi italiani usano i nomi ufficiali della versione italiana del gioco (nomi dei personaggi:
vedi `data/effects.json` → `characters`). Se il nome italiano di un'arma non è noto, ripeti quello inglese.

### `ratings.json`

Regole con espressioni regolari sul **nome italiano** dell'effetto, voti 0-5 (vale la prima che
corrisponde; `solo_score` è il voto in solitaria). Aggiorna i voti perché siano coerenti con le
tier list: S = 5, A = 4, B = 3, C = 2, inutile = 0-1. Non cambiare la struttura del file.

### `meta.json`

```json
{
  "updated": "AAAA-MM-GG",
  "game_version": "versione o patch più recente trovata",
  "changes": [{"it": "...", "en": "..."}],
  "sources": [{"title": "...", "url": "https://..."}]
}
```

`changes` elenca in poche righe cosa è cambiato rispetto alla versione precedente.

## 3. Validazione e commit

```
python tools/validate_research.py
```

Se fallisce, correggi e rilancia. Solo quando passa: commit su `main` con messaggio
`Ricerca mensile AAAA-MM-GG` e push. Non toccare file fuori da `research/` e `data/`.
