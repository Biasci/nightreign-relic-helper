"""Controlla i file di research/ prima del commit. Esce con codice 1 se qualcosa non va."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS = {"S", "A", "B", "C"}
CHARACTERS = {"Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
              "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"}
MAX_UNKNOWN_SHARE = 0.1  # tollera pochi nomi non trovati (es. effetti appena aggiunti)

errors, warnings = [], []


def load(name):
    try:
        return json.loads((ROOT / "research" / name).read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{name}: JSON non valido ({exc})")
        return None


def bilingual(value, where):
    if not (isinstance(value, dict) and value.get("it") and value.get("en")):
        errors.append(f"{where}: servono i testi 'it' e 'en'")


def main():
    effects = json.loads((ROOT / "data" / "effects.json").read_text(encoding="utf-8"))["effects"]
    known = {e["name_en"] for e in effects.values()}

    meta = load("meta.json")
    if meta is not None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get("updated", "")):
            errors.append("meta.json: 'updated' deve essere AAAA-MM-GG")
        if not meta.get("sources"):
            errors.append("meta.json: nessuna fonte")
        for i, change in enumerate(meta.get("changes", [])):
            bilingual(change, f"meta.json changes[{i}]")

    ratings = load("ratings.json")
    if ratings is not None:
        for kind in ("effects", "curses"):
            for rule in ratings.get(kind, []):
                try:
                    patterns = [rule[k] for k in ("match_en", "match") if k in rule]
                    if not patterns:
                        raise ValueError("serve 'match_en' o 'match'")
                    for p in patterns:
                        re.compile(p)
                    float(rule["score"])
                except Exception as exc:
                    errors.append(f"ratings.json {kind}: regola {rule!r} non valida ({exc})")

    data = load("characters.json")
    if data is None:
        return report()
    chars = data.get("characters", {})
    missing = CHARACTERS - set(chars)
    if missing:
        errors.append(f"characters.json: mancano {sorted(missing)}")

    names, unknown = 0, []

    def check_effect(name, where):
        nonlocal names
        names += 1
        if name not in known:
            unknown.append(f"{where}: {name}")

    for key, c in chars.items():
        if c.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"{key}: 'confidence' non valida")
        bilingual(c.get("summary"), f"{key}.summary")
        for section in ("relic_effects", "deep_effects"):
            for i, e in enumerate(c.get(section, [])):
                if e.get("tier") not in TIERS:
                    errors.append(f"{key}.{section}[{i}]: tier non valido")
                check_effect(e.get("effect"), f"{key}.{section}")
                bilingual(e.get("why"), f"{key}.{section}[{i}].why")
        for group in ("harmless", "avoid"):
            for e in c.get("curses", {}).get(group, []):
                check_effect(e.get("curse"), f"{key}.curses.{group}")
        for section, field in (("weapon_passives", "passive"), ("weapons", "name")):
            for i, w in enumerate(c.get(section, [])):
                if w.get("tier") not in TIERS:
                    errors.append(f"{key}.{section}[{i}]: tier non valido")
                bilingual(w.get(field), f"{key}.{section}[{i}].{field}")
        for i, b in enumerate(c.get("builds", [])):
            bilingual(b.get("name"), f"{key}.builds[{i}].name")
            for name in b.get("normal", []) + b.get("deep", []):
                check_effect(name, f"{key}.builds[{i}]")

    for name in data.get("general", {}).get("solo_useless", []):
        check_effect(name, "general.solo_useless")

    if unknown:
        share = len(unknown) / max(names, 1)
        (errors if share > MAX_UNKNOWN_SHARE else warnings).append(
            f"{len(unknown)}/{names} nomi di effetto non trovati in data/effects.json:\n  " + "\n  ".join(unknown))
    return report()


def report():
    for w in warnings:
        print("ATTENZIONE:", w)
    for e in errors:
        print("ERRORE:", e)
    print("OK" if not errors else f"{len(errors)} errori")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
