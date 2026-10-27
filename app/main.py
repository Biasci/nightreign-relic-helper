"""Avvia il server locale e apre l'interfaccia in una finestra di Edge in modalità app.

Il server ascolta solo su 127.0.0.1 e si chiude da solo quando la finestra non
manda più segnali per un po'.
"""
import copy
import json
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import research
from analysis import Ratings, analyze
from paths import UI_DIR
from save_reader import GameData, find_saves, read_save

IDLE_TIMEOUT = 30  # secondi senza segnali dalla finestra prima di chiudere

game = GameData()
EFFECT_NAMES_IT = {e["name_en"]: e["name_it"] for e in game.effects.values()}
cache = {}  # percorso -> (mtime, reliquie)
last_ping = time.time()
update = {"state": "checking", "updated": None, "error": None}


def check_update():
    try:
        new = research.check_for_update()
        update.update(state="new" if new else "current", updated=new)
    except Exception as exc:  # offline o repository non raggiungibile: si usano i dati locali
        update.update(state="error", error=str(exc))


def saves_info():
    return [{"path": str(p), "name": p.name, "mtime": p.stat().st_mtime, "size": p.stat().st_size}
            for p in find_saves()]


def allowed_save(path):
    """Si leggono solo i salvataggi trovati nella cartella di Nightreign."""
    return path in {s["path"] for s in saves_info()}


def load(path, force=False):
    mtime = Path(path).stat().st_mtime
    hit = cache.get(path)
    if hit and hit[0] == mtime and not force:
        return hit
    cache[path] = (mtime, [asdict(r) for r in read_save(path, game)])
    return cache[path]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def log_message(self, *args):
        pass

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global last_ping
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        if not url.path.startswith("/api/"):
            return super().do_GET()

        last_ping = time.time()
        if url.path == "/api/saves":
            return self.send_json({"saves": saves_info(), "characters": game.characters})
        if url.path == "/api/research":
            return self.send_json({"meta": research.load("meta.json"), "update": update})
        if url.path == "/api/characters":
            # I nomi degli effetti nella ricerca sono in inglese: si aggiungono quelli italiani del gioco.
            return self.send_json({**research.load("characters.json"), "names_it": EFFECT_NAMES_IT})

        path = query.get("path", "")
        if not allowed_save(path):
            return self.send_json({"error": "Salvataggio non trovato."}, 404)
        if url.path == "/api/status":
            return self.send_json({"mtime": Path(path).stat().st_mtime})
        if url.path == "/api/relics":
            try:
                mtime, relics = load(path, force=query.get("force") == "1")
            except Exception as exc:  # il gioco potrebbe star scrivendo il file proprio ora
                return self.send_json({"error": f"Lettura non riuscita: {exc}"}, 503)
            try:
                # I voti si rileggono ogni volta: valgono subito sia gli aggiornamenti sia my_ratings.json.
                ratings = Ratings(solo=query.get("solo", "1") == "1")
            except Exception as exc:
                return self.send_json({"error": f"File dei voti non valido: {exc}"}, 500)
            analyzed = analyze(copy.deepcopy(relics), list(game.characters), ratings)
            return self.send_json({"mtime": mtime, "relics": analyzed})
        self.send_json({"error": "Richiesta sconosciuta."}, 404)


def open_window(url):
    edge = shutil.which("msedge") or next(
        (p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                     r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if Path(p).exists()), None)
    if edge:
        subprocess.Popen([edge, f"--app={url}", "--window-size=1280,860"])
    else:
        webbrowser.open(url)


def main():
    # Per lo sviluppo: --dev [porta] non apre la finestra e non si chiude da solo.
    dev = "--dev" in sys.argv
    port = int(sys.argv[-1]) if dev and sys.argv[-1].isdigit() else 0
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Nightreign Relic Helper in esecuzione su {url}", flush=True)
    threading.Thread(target=check_update, daemon=True).start()
    if dev:
        return server.serve_forever()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    open_window(url)
    while time.time() - last_ping < IDLE_TIMEOUT:
        time.sleep(2)
    server.shutdown()


if __name__ == "__main__":
    main()
