"""Dati della ricerca (voti degli effetti, tier list, armi, build) e loro aggiornamento.

La routine mensile aggiorna la cartella research/ del repository GitHub. All'avvio l'app
confronta research/meta.json online con quello locale e, se è più recente, scarica i file
nella cartella utente. I file scaricati vengono validati prima di sostituire quelli vecchi:
se qualcosa non va, l'app continua con i dati che aveva.
"""
import json
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path

from paths import BUNDLED_RESEARCH, DOWNLOADED_RESEARCH, RAW_URL

FILES = ("meta.json", "ratings.json", "characters.json")
TIMEOUT = 15


def read_meta(folder):
    try:
        return json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def current_dir():
    """La cartella più aggiornata tra quella inclusa nell'app e quella scaricata."""
    bundled, downloaded = read_meta(BUNDLED_RESEARCH), read_meta(DOWNLOADED_RESEARCH)
    if downloaded and all((DOWNLOADED_RESEARCH / f).exists() for f in FILES) \
            and downloaded.get("updated", "") >= (bundled or {}).get("updated", ""):
        return DOWNLOADED_RESEARCH
    return BUNDLED_RESEARCH


def load(name):
    return json.loads((current_dir() / name).read_text(encoding="utf-8"))


def validate(folder):
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get("updated", "")):
        raise ValueError("meta.json: data 'updated' mancante")
    ratings = json.loads((folder / "ratings.json").read_text(encoding="utf-8"))
    for rule in ratings["effects"] + ratings["curses"]:
        patterns = [rule[k] for k in ("match_en", "match") if k in rule]
        if not patterns:
            raise ValueError(f"ratings.json: regola senza 'match_en' o 'match': {rule}")
        for p in patterns:
            re.compile(p)
        float(rule["score"])
    characters = json.loads((folder / "characters.json").read_text(encoding="utf-8"))
    if not isinstance(characters.get("characters"), dict) or not characters["characters"]:
        raise ValueError("characters.json: nessun personaggio")


def fetch(name):
    with urllib.request.urlopen(f"{RAW_URL}/{name}", timeout=TIMEOUT) as res:
        return res.read()


def check_for_update():
    """Scarica i dati nuovi se ci sono. Restituisce la data dei nuovi dati, oppure None."""
    remote = json.loads(fetch("meta.json"))
    local = read_meta(current_dir()) or {}
    if remote.get("updated", "") <= local.get("updated", ""):
        return None

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in FILES:
            (tmp / name).write_bytes(fetch(name))
        validate(tmp)
        DOWNLOADED_RESEARCH.parent.mkdir(parents=True, exist_ok=True)
        staging = DOWNLOADED_RESEARCH.with_name("research.new")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(tmp, staging)
    shutil.rmtree(DOWNLOADED_RESEARCH, ignore_errors=True)
    staging.rename(DOWNLOADED_RESEARCH)
    return remote["updated"]
