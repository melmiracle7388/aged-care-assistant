"""Picture-tile records: staff tap what happened (one or many tiles) and save one entry.

The tiles are fixed (data/record_tiles.json). Each tile has a plain sentence, so the saved note reads well in the
daily notes and the shift handover. No AI is needed to save a record, so it cannot invent anything.
A tile may carry a level: "check" (tell the RN, not urgent) or "urgent" (fall, choking: use the emergency steps).
"""
import json
from datetime import datetime

import store
from config import DATA, LOG_DIR

RECORDS_FILE = LOG_DIR / "records.jsonl"
LEVELS = {"": 0, "check": 1, "urgent": 2}


def sections():
    return json.loads((DATA / "record_tiles.json").read_text())


def tile_index():
    """{tile id: (section name, tile)}"""
    return {t["id"]: (s["name"], t) for s in sections() for t in s["tiles"]}


def chosen(ids):
    idx = tile_index()
    return [idx[i] for i in ids if i in idx]


def sentence(ids, extra=""):
    """The note text for the chosen tiles, in the order they were tapped, plus the optional typed note."""
    parts = [t["text"] for _, t in chosen(ids)]
    if (extra or "").strip():
        parts.append(extra.strip())
    return " ".join(parts)


def level(ids):
    """The most serious level among the chosen tiles: "", "check" or "urgent"."""
    best = ""
    for _, t in chosen(ids):
        lv = t.get("level", "")
        if LEVELS[lv] > LEVELS[best]:
            best = lv
    return best


def urgent_kind(ids):
    """Which emergency steps to show (a key of rules.STEPS) for an urgent tile, or "other"."""
    for _, t in chosen(ids):
        if t.get("level") == "urgent":
            return t.get("kind", "other")
    return "other"


def add(resident, staff, ids, extra=""):
    """Save the record (structured, for later review and models) and a note (for daily notes and handover)."""
    ids = [i for i in ids if i in tile_index()]
    if not ids:
        raise ValueError("no tiles chosen")
    LOG_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    names = []
    for sec, _ in chosen(ids):
        if sec not in names:
            names.append(sec)
    rec = {"resident_id": resident["id"], "date": now.date().isoformat(), "time": now.strftime("%H:%M"),
           "staff": staff.split(",")[0].strip(), "tiles": ids, "sections": names, "level": level(ids),
           "note": (extra or "").strip()}
    with RECORDS_FILE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    store.add_note(resident, staff, sentence(ids, extra), tags=["Picture record"] + names)
    return rec
