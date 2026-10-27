"""Genera data/relics.json e data/effects.json a partire dai param e dai testi del gioco.

Sorgente: la cartella Resources di alfizari/Elden-Ring-Nightreign-Save-Editor (licenza MIT),
che contiene i param estratti (CSV) e i testi localizzati (FMG in XML).

Uso: python tools/build_data.py <cartella Resources>
"""
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"

CHARACTERS = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
              "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"]
COLORS = {0: "red", 1: "blue", 2: "yellow", 3: "green"}
NO_EFFECT = -1


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_fmg(text_dir, lang, name):
    """Unisce il file base e quello del DLC: id -> testo."""
    names = {}
    for suffix in ("", "_dlc01"):
        path = text_dir / lang / f"{name}{suffix}.fmg.xml"
        if not path.exists():
            continue
        for node in ET.parse(path).getroot().iter("text"):
            value = " ".join((node.text or "").split())
            if value and value != "%null%":
                names[int(node.get("id"))] = value
    return names


def italian_character_names(effects):
    """Ricava i nomi italiani dei personaggi dal prefisso "[Nome]" dei loro effetti esclusivi."""
    names = {}
    for char in CHARACTERS:
        prefixes = Counter()
        for eff in effects.values():
            if eff["characters"] == [char]:
                m = re.match(r"\[([^\]]+)\]", eff["name_it"])
                if m:
                    prefixes[m.group(1)] += 1
        names[char] = prefixes.most_common(1)[0][0] if prefixes else char
    return names


def main(resources):
    params, text = resources / "Param", resources / "Text"

    effect_it = read_fmg(text, "it_IT", "AttachEffectName")
    effect_en = read_fmg(text, "en_US", "AttachEffectName")
    effects = {}
    for row in read_csv(params / "AttachEffectParam.csv"):
        eid, text_id = int(row["ID"]), int(row["attachTextId"])
        if text_id not in effect_it and text_id not in effect_en:
            continue
        allowed = [c for c in CHARACTERS if row.get(f"allow{c}") == "1"]
        effects[eid] = {
            "name_it": effect_it.get(text_id) or effect_en[text_id],
            "name_en": effect_en.get(text_id) or effect_it[text_id],
            # Effetti con lo stesso gruppo di compatibilità non si sommano tra loro.
            "group": int(row["compatibilityId"]),
            "debuff": row["isDebuff"] == "1",
            # Lista vuota = utilizzabile da tutti.
            "characters": [] if len(allowed) == len(CHARACTERS) else allowed,
        }

    relic_it = read_fmg(text, "it_IT", "AntiqueName")
    relic_en = read_fmg(text, "en_US", "AntiqueName")
    relics = {}
    for row in read_csv(params / "EquipParamAntique.csv"):
        rid = int(row["ID"])
        if rid not in relic_it and rid not in relic_en:
            continue
        slots = sum(int(row[f"attachEffectTableId_{i}"]) != NO_EFFECT for i in (1, 2, 3))
        relics[rid] = {
            "name_it": relic_it.get(rid) or relic_en[rid],
            "name_en": relic_en.get(rid) or relic_it[rid],
            "color": COLORS.get(int(row["relicColor"]), "unknown"),
            "deep": row["isDeepRelic"] == "1",
            "slots": slots,
        }

    OUT.mkdir(exist_ok=True)
    (OUT / "effects.json").write_text(json.dumps(
        {"characters": italian_character_names(effects), "effects": effects},
        ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "relics.json").write_text(json.dumps(relics, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(effects)} effetti, {len(relics)} reliquie -> {OUT}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
