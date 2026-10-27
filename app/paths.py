"""Percorsi dell'app, validi sia da sorgente sia dentro l'eseguibile creato con PyInstaller."""
import os
import sys
from pathlib import Path

# File inclusi nell'app (interfaccia, tabelle del gioco, dati della ricerca di partenza).
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
UI_DIR = BUNDLE / "app" / "ui"
DATA_DIR = BUNDLE / "data"
BUNDLED_RESEARCH = BUNDLE / "research"

# Dati scaricati dagli aggiornamenti: restano tra un avvio e l'altro e tra una versione e l'altra.
USER_DIR = Path(os.environ.get("APPDATA", Path.home())) / "NightreignRelicHelper"
DOWNLOADED_RESEARCH = USER_DIR / "research"

# Il repository da cui arrivano gli aggiornamenti mensili della ricerca.
REPO = "Biasci/nightreign-relic-helper"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/research"
