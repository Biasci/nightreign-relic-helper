"""Valutazione delle reliquie e consigli su quali buttare.

Tre motivi, dal più sicuro al più soggettivo:
- doppione: identica a un'altra reliquia (stesso colore, tipo, effetti e malus);
- superata: un'altra reliquia dello stesso colore e tipo ha tutti i suoi effetti
  (allo stesso livello o superiore) e malus non peggiori;
- poco utile: il punteggio migliore, su tutti i personaggi, resta sotto la soglia
  e nessun effetto vale 4 o più.
"""
import json
import re
from collections import defaultdict

import research
from paths import USER_DIR

MY_RATINGS = USER_DIR / "my_ratings.json"

LEVEL = re.compile(r"^(.*?)\s*\+(\d+)$")


def split_level(name):
    """"Vitalità +3" -> ("vitalità", 3); senza "+N" il livello è 0."""
    m = LEVEL.match(name)
    return (m.group(1).lower(), int(m.group(2))) if m else (name.lower(), 0)


class Ratings:
    def __init__(self, solo=True):
        data = research.load("ratings.json")
        # I voti personali hanno la precedenza e non vengono toccati dagli aggiornamenti.
        if MY_RATINGS.exists():
            mine = json.loads(MY_RATINGS.read_text(encoding="utf-8"))
            data["effects"] = mine.get("effects", []) + data["effects"]
            data["curses"] = mine.get("curses", []) + data["curses"]
        self.solo = solo
        self.default_score = data["default_score"]
        self.default_curse = data["default_curse"]
        self.effect_rules = [self.compile(r) for r in data["effects"]]
        self.curse_rules = [self.compile(r) for r in data["curses"]]

    @staticmethod
    def compile(rule):
        """Una regola cerca nel nome inglese ('match_en') e/o in quello italiano ('match')."""
        return (re.compile(rule["match_en"], re.I) if "match_en" in rule else None,
                re.compile(rule["match"], re.I) if "match" in rule else None,
                rule)

    @staticmethod
    def find(rules, item):
        for rx_en, rx_it, rule in rules:
            if (rx_en and rx_en.search(item["name_en"])) or (rx_it and rx_it.search(item["name"])):
                return rule
        return None

    def effect(self, effect):
        rule = self.find(self.effect_rules, effect)
        if rule is None:
            return self.default_score
        return rule.get("solo_score", rule["score"]) if self.solo else rule["score"]

    def curse(self, curse):
        rule = self.find(self.curse_rules, curse)
        return self.default_curse if rule is None else rule["score"]


def score_for(relic, character, ratings):
    """Punteggio della reliquia per un personaggio: gli effetti riservati ad altri valgono 0,
    i malus pesano sempre."""
    total = 0
    for e in relic["effects"]:
        if not e["characters"] or character in e["characters"]:
            total += ratings.effect(e)
        if e["curse"]:
            total += ratings.curse(e["curse"])
    return total


def signature(relic):
    return (relic["color"], relic["deep"],
            tuple(sorted((e["id"], e["curse"]["id"] if e["curse"] else 0) for e in relic["effects"])))


def covers(better, worse, ratings):
    """True se `better` ha tutti gli effetti di `worse` (livello >= ) e malus non peggiori."""
    available = list(better["_levels"])
    for base, level in worse["_levels"]:
        match = next((i for i, (b, l) in enumerate(available) if b == base and l >= level), None)
        if match is None:
            return False
        available.pop(match)
    return better["_curse"] >= worse["_curse"]


def analyze(relics, characters, ratings):
    for r in relics:
        r["_levels"] = [split_level(e["name"]) for e in r["effects"]]
        r["_curse"] = sum(ratings.curse(e["curse"]) for e in r["effects"] if e["curse"])
        r["scores"] = {c: score_for(r, c, ratings) for c in characters}
        r["best"] = max(r["scores"].values(), default=0)
        r["best_for"] = [c for c, s in r["scores"].items() if s == r["best"]]
        r["top_effect"] = max((ratings.effect(e) for e in r["effects"]), default=0)
        r["effect_scores"] = [ratings.effect(e) for e in r["effects"]]

    verdicts = {}

    # 1. Doppioni: si tiene la più recente di ogni gruppo.
    groups = defaultdict(list)
    for r in relics:
        groups[signature(r)].append(r)
    for same in groups.values():
        same.sort(key=lambda r: r["order"], reverse=True)
        for r in same[1:]:
            verdicts[r["uid"]] = {"kind": "duplicate", "keep": same[0]["uid"]}

    # 2. Superate: confronto tra reliquie dello stesso colore e tipo, escludendo i doppioni.
    by_slot = defaultdict(list)
    for r in relics:
        if r["uid"] not in verdicts:
            by_slot[(r["color"], r["deep"])].append(r)
    for pool in by_slot.values():
        for worse in pool:
            bases = {b for b, _ in worse["_levels"]}
            for better in pool:
                if better is worse or not bases <= {b for b, _ in better["_levels"]}:
                    continue
                # A pari merito (si coprono a vicenda) vince la più recente, così non spariscono entrambe.
                if covers(better, worse, ratings) and not (
                        covers(worse, better, ratings) and worse["order"] > better["order"]):
                    verdicts[worse["uid"]] = {"kind": "dominated", "keep": better["uid"]}
                    break

    # 3. Le "poco utili" le decide l'interfaccia con la soglia scelta (best < soglia e top_effect < 4).
    for r in relics:
        for key in ("_levels", "_curse"):
            del r[key]
        r["verdict"] = verdicts.get(r["uid"])
    return relics
