"""Lettura in sola lettura dei salvataggi di Elden Ring Nightreign (.sl2).

Il file non viene mai modificato: viene letto in memoria, decifrato e analizzato.

Formato (documentato dalla community, vedi NOTICE.md):
- contenitore BND4 con N voci; ogni voce è cifrata AES-128-CBC, i primi 16 byte sono l'IV;
- nella voce 0 ogni reliquia è un blocco da 80 byte:
    +0  id istanza (byte alto 0xC0)    +4  id oggetto | 0x80000000
    +16 4 id effetti                   +56 4 id malus (uno per effetto)
- una reliquia è nell'inventario se il suo id istanza compare seguito da 01 00 00 00.
"""
import json
import os
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from paths import DATA_DIR

KEY = bytes.fromhex("18f6326605bd178a5524523ac0a0c609")
EMPTY = 0xFFFFFFFF
SLOT_SIZE = 80


@dataclass
class Effect:
    id: int
    name: str  # italiano: è anche il nome su cui lavorano i voti in ratings.json
    name_en: str
    group: int
    characters: list
    curse: dict | None = None  # malus legato a questo effetto (reliquie profonde)


@dataclass
class Relic:
    uid: int
    item_id: int
    name: str
    name_en: str
    color: str
    deep: bool
    effects: list = field(default_factory=list)
    order: int = 0  # posizione nell'inventario (più alto = più recente)
    unknown: bool = False


class GameData:
    def __init__(self, data_dir=DATA_DIR):
        effects = json.loads((data_dir / "effects.json").read_text(encoding="utf-8"))
        self.characters = effects["characters"]
        self.effects = {int(k): v for k, v in effects["effects"].items()}
        relics = json.loads((data_dir / "relics.json").read_text(encoding="utf-8"))
        self.relics = {int(k): v for k, v in relics.items()}

    def effect(self, eid):
        info = self.effects.get(eid)
        if info is None:
            return Effect(eid, f"Effetto sconosciuto ({eid})", f"Unknown effect ({eid})", eid, [])
        return Effect(eid, info["name_it"], info["name_en"], info["group"], info["characters"])


def find_saves():
    """Tutti i file .sl2 / .co2 nella cartella di Nightreign, il più recente per primo."""
    base = Path(os.environ.get("APPDATA", "")) / "Nightreign"
    saves = [p for p in base.glob("*/*") if p.suffix.lower() in (".sl2", ".co2")]
    return sorted(saves, key=lambda p: p.stat().st_mtime, reverse=True)


def decrypt_entries(raw: bytes):
    if raw[:4] != b"BND4":
        raise ValueError("Non è un salvataggio di Nightreign (manca l'intestazione BND4).")
    count = struct.unpack_from("<i", raw, 12)[0]
    entries = []
    for i in range(count):
        size, _, offset = struct.unpack_from("<iii", raw, 64 + 32 * i + 8)
        blob = raw[offset:offset + size]
        dec = Cipher(algorithms.AES(KEY), modes.CBC(blob[:16])).decryptor()
        entries.append((dec.update(blob[16:]) + dec.finalize())[4:])
    return entries


def inventory_order(data: bytes):
    """id istanza -> posizione nell'inventario, per le reliquie realmente possedute."""
    order = {}
    pos = data.find(b"\x01\x00\x00\x00", 4)
    while pos != -1:
        uid = struct.unpack_from("<I", data, pos - 4)[0]
        if uid >> 24 == 0xC0 and uid not in order:
            order[uid] = struct.unpack_from("<H", data, pos + 4)[0]
        pos = data.find(b"\x01\x00\x00\x00", pos + 1)
    return order


def parse_relics(data: bytes, game: GameData):
    owned = inventory_order(data)
    relics = {}
    for pos in range(0, len(data) - SLOT_SIZE):
        if data[pos + 3] != 0xC0 or data[pos + 7] != 0x80 or data[pos + 11] != 0x80:
            continue
        uid = struct.unpack_from("<I", data, pos)[0]
        if uid in relics or uid not in owned:
            continue
        item_id = struct.unpack_from("<I", data, pos + 4)[0] & 0x7FFFFFFF
        effect_ids = struct.unpack_from("<4I", data, pos + 16)
        curse_ids = struct.unpack_from("<4I", data, pos + 56)
        if all(e == EMPTY for e in effect_ids) or any(e != EMPTY and e >= 1 << 24 for e in effect_ids):
            continue

        info = game.relics.get(item_id)
        relic = Relic(
            uid=uid,
            item_id=item_id,
            name=info["name_it"] if info else f"Reliquia sconosciuta ({item_id})",
            name_en=info["name_en"] if info else f"Unknown relic ({item_id})",
            color=info["color"] if info else "unknown",
            deep=info["deep"] if info else False,
            order=owned[uid],
            unknown=info is None,
        )
        for eid, cid in zip(effect_ids, curse_ids):
            if eid == EMPTY:
                continue
            effect = game.effect(eid)
            if cid != EMPTY:
                c = game.effect(cid)
                effect.curse = {"id": c.id, "name": c.name, "name_en": c.name_en}
            relic.unknown |= eid not in game.effects
            relic.effects.append(effect)
        relics[uid] = relic
    return sorted(relics.values(), key=lambda r: r.order, reverse=True)


def read_save(path, game: GameData):
    raw = Path(path).read_bytes()  # sola lettura
    entries = decrypt_entries(raw)
    return parse_relics(entries[0], game)


if __name__ == "__main__":
    import sys
    from collections import Counter

    game = GameData()
    path = sys.argv[1] if len(sys.argv) > 1 else find_saves()[0]
    relics = read_save(path, game)
    print(f"{path}: {len(relics)} reliquie")
    print(Counter((r.color, r.deep) for r in relics))
    print("sconosciute:", sum(r.unknown for r in relics))
    for r in relics[:5]:
        print(f"- {r.name} [{r.color}{', profonda' if r.deep else ''}]")
        for e in r.effects:
            print(f"    {e.name}" + (f"  (malus: {e.curse['name']})" if e.curse else ""))
