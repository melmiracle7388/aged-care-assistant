"""Reads the fake data and keeps the alert list and search log (plain files, demo only)."""
import json
from datetime import date, datetime

from chunker import split_sections
from config import DATA, LOG_DIR

ALERTS_FILE = LOG_DIR / "alerts.json"
SEARCH_LOG = LOG_DIR / "search_log.jsonl"
NOTES_FILE = LOG_DIR / "notes.jsonl"


# ---------- data ----------
def residents_meta():
    items = json.loads((DATA / "residents_meta.json").read_text())
    return sorted(items, key=lambda r: int(r["room"]))


def roster():
    return json.loads((DATA / "roster.json").read_text())


def resident_sections(rid):
    path = next((DATA / "residents").glob(f"{rid}_*.md"))
    _, sections = split_sections(path.read_text())
    return dict(sections)


def _seeded_notes(rid):
    path = next((DATA / "notes").glob(f"{rid}_*_notes.md"), None)
    if path is None:
        return []
    out, day = [], ""
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            day = line[3:].strip()
        elif line.startswith("- ") and line.count(" | ") >= 2:
            time_, staff, text = (p.strip() for p in line[2:].split(" | ", 2))
            out.append({"day": day, "time": time_, "staff": staff, "text": text})
    return out


def _saved_notes(rid):
    """Notes saved from the app (typed or spoken), kept in logs/notes.jsonl."""
    if not NOTES_FILE.exists():
        return []
    out = []
    for line in NOTES_FILE.read_text().splitlines():
        try:
            n = json.loads(line)
        except Exception:
            continue
        if n.get("resident_id") == rid and n.get("text"):
            out.append(n)
    return out


def notes_for(rid):
    """All notes of one resident: a list of {day, time, staff, text}. Today first, older days after.

    Notes saved in the app today join the fake "Today" notes, in time order.
    """
    seeded = _seeded_notes(rid)
    today = [n for n in seeded if n["day"] == "Today"]
    older = [n for n in seeded if n["day"] != "Today"]
    for n in _saved_notes(rid):
        entry = {"day": "Today", "time": n["time"], "staff": n["staff"], "text": n["text"],
                 "tags": n.get("tags", []), "saved": True}
        if n.get("date") == date.today().isoformat():
            today.append(entry)
        else:
            entry["day"] = n.get("date", "Earlier")
            older.append(entry)
    today.sort(key=lambda n: n["time"])
    return today + older


def add_note(resident, staff, text, original="", tags=()):
    """Save a care note written in the app. `staff` is the signed-in name; only the name part is kept."""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    LOG_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    rec = {"resident_id": resident["id"], "date": now.date().isoformat(), "time": now.strftime("%H:%M"),
           "staff": staff.split(",")[0].strip(), "text": text, "original": (original or "").strip(),
           "tags": list(tags), "saved_at": now.isoformat(timespec="seconds")}
    with NOTES_FILE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# ---------- alerts ----------
def _read_alerts():
    if not ALERTS_FILE.exists():
        return []
    try:
        return json.loads(ALERTS_FILE.read_text())
    except Exception:
        return []


def _write_alerts(items):
    LOG_DIR.mkdir(exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(items, indent=2))


def add_alert(level, resident, what, steps, by):
    items = _read_alerts()
    aid = (items[-1]["id"] + 1) if items else 1
    items.append({
        "id": aid, "level": level, "resident_id": resident["id"], "resident": resident["name"],
        "room": resident["room"], "what": what, "steps": steps, "by": by,
        "time": datetime.now().strftime("%I:%M %p").lstrip("0"), "status": "sent",
    })
    _write_alerts(items)
    return aid


def all_alerts():
    return _read_alerts()


def alerts_for(rid):
    return [a for a in _read_alerts() if a["resident_id"] == rid]


def get_alert(aid):
    return next((a for a in _read_alerts() if a["id"] == aid), None)


def ack_alert(aid):
    items = _read_alerts()
    for a in items:
        if a["id"] == aid:
            a["status"] = "ack"
    _write_alerts(items)


# ---------- search log ----------
def log_search(staff, resident_id, question, level, sources, found):
    LOG_DIR.mkdir(exist_ok=True)
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"), "staff": staff,
        "resident_id": resident_id, "question": question, "level": level,
        "sources": sources, "found": found,
    }
    with SEARCH_LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------- training results ----------
TRAINING_FILE = LOG_DIR / "training.jsonl"


def add_training_result(staff, topic, score, total, source="bank"):
    LOG_DIR.mkdir(exist_ok=True)
    rec = {"date": date.today().isoformat(), "time": datetime.now().strftime("%H:%M"), "staff": staff.split(",")[0].strip(),
           "topic": topic, "score": int(score), "total": int(total), "source": source}
    with TRAINING_FILE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def training_history(staff, limit=5):
    if not TRAINING_FILE.exists():
        return []
    name = staff.split(",")[0].strip()
    out = []
    for line in TRAINING_FILE.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("staff") == name:
            out.append(r)
    return out[-limit:][::-1]
