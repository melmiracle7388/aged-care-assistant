"""The care chart: one tile per care item for a resident's day (meals, drinks, toilet, wash, repositioning...).

Tiles come from a shared daily routine (data/chart_routine.json) plus the resident's own care plan tasks
(data/care_tasks.json). A tile is white until it is due, amber when due, red when late, and green with a tick once done.
What the care worker records (how much was eaten, how much was drunk, pain level) is saved with the tick and
flows into the shift handover. No AI here: the chart is fixed, so it cannot invent anything.
"""
import json
import re
from datetime import datetime, timedelta

import tasks
from config import DATA

FLUID_TARGET_ML = 1500
MEAL_OPTIONS = ["All", "Most", "Half", "A quarter", "Refused"]
FLUID_OPTIONS = ["100 ml", "150 ml", "200 ml", "250 ml", "300 ml", "Refused"]
PAIN_OPTIONS = ["No pain", "Mild", "Moderate", "Severe"]
OPTIONS = {"meal": MEAL_OPTIONS, "fluid": FLUID_OPTIONS, "pain": PAIN_OPTIONS}
# care plan task id ending -> tile label and icon
PLAN_TILES = {"reposition": ("Reposition", "sync"), "aid": ("Hearing aid check", "hearing"), "aids": ("Hearing aids in", "hearing"),
              "bed": ("Bed safety check", "bed"), "night": ("Night round", "bedtime"), "toilet": ("Toilet after meal", "wc"),
              "upright": ("Sit upright", "event_seat")}
MEAL_KEYS = {"breakfast": "breakfast", "lunch": "lunch", "tea": "tea"}


def routine():
    return json.loads((DATA / "chart_routine.json").read_text())


def _state(minutes, done):
    if done:
        return "done"
    if minutes < -tasks.MISSED_MINUTES:
        return "missed"
    if minutes < -tasks.GRACE_MINUTES:
        return "overdue"
    if minutes <= 0:
        return "due"
    if minutes <= tasks.SOON_MINUTES:
        return "soon"
    return "later"


def tiles(rid, now=None):
    """Every tile of today's chart for one resident, sorted by time. See _state for the states."""
    now = now or datetime.now()
    done = {(r["task_id"], r["due"]): r for r in tasks._records(now.date().isoformat())}
    plan = tasks.load_tasks().get(rid, [])
    meal_note = {}
    for task in plan:
        for meal in task["when"].get("meals", []):
            meal_note[meal] = task
    out = []

    def add(task_id, due, label, icon, ask, note, source):
        due_dt = datetime.combine(now.date(), tasks._hm(due))
        minutes = (due_dt - now).total_seconds() / 60
        rec = done.get((task_id, due))
        out.append({"resident_id": rid, "task_id": task_id, "due": due, "label": label, "icon": icon, "ask": ask, "note": note,
                    "source": source, "state": _state(minutes, bool(rec)), "value": (rec or {}).get("value", ""),
                    "done_by": (rec or {}).get("by", ""), "done_at": (rec or {}).get("at", "")})

    for item in routine():
        for due in item["times"]:
            task_id, note, source = f"{rid}-r-{item['key']}", "", "Daily routine"
            meal = MEAL_KEYS.get(item["key"])
            if meal and meal in meal_note:  # the same tick as the care plan's meal task, so every screen agrees
                task = meal_note[meal]
                task_id, note, source = task["id"], task["text"], task["source"]
            add(task_id, due, item["label"], item["icon"], item["ask"], note, source)
    for task in plan:
        if task["when"].get("meals"):
            continue
        suffix = task["id"].split("-", 1)[1]
        label, icon = PLAN_TILES.get(suffix, (" ".join(task["text"].split()[:3]).rstrip(".,"), "checklist"))
        for due, extra in tasks.occurrences(task):
            add(task["id"], due, label + (f" ({extra})" if extra else ""), icon, "", task["text"], task["source"])
    out.sort(key=lambda t: (t["due"] < "05:00", t["due"]))  # the small hours go last
    return out


def ml(value):
    m = re.match(r"(\d+)\s*ml", value or "")
    return int(m.group(1)) if m else 0


def fluids(rid, now=None):
    """{had, target, expected, behind}: millilitres drunk so far against what is expected by this time of day."""
    now = now or datetime.now()
    had = sum(ml(t["value"]) for t in tiles(rid, now) if t["ask"] == "fluid" and t["state"] == "done")
    hours = max(0.0, min(1.0, (now.hour + now.minute / 60 - 6) / 16))
    expected = int(FLUID_TARGET_ML * hours)
    return {"had": had, "target": FLUID_TARGET_ML, "expected": expected, "behind": now.hour >= 10 and had < 0.6 * expected}


def meals(rid, now=None):
    """{eaten, due}: meals recorded so far and meals that should be done by now."""
    ts = [t for t in tiles(rid, now) if t["ask"] == "meal"]
    return {"eaten": sum(t["state"] == "done" for t in ts),
            "due": sum(t["state"] in ("done", "due", "overdue", "missed") for t in ts), "total": len(ts)}


def record_lines(rid, now=None):
    """Recorded care for the handover: [{time, staff, text, tags}] for today's ticks that carry a value or a care step."""
    out = []
    for t in tiles(rid, now):
        if t["state"] != "done":
            continue
        v = t["value"]
        if t["ask"] == "meal":
            text = f"{t['label']}: " + ("refused the meal." if v == "Refused" else f"ate {v.lower()}." if v else "recorded.")
            if v == "A quarter":
                text = f"{t['label']}: ate a quarter."
        elif t["ask"] == "fluid":
            text = f"{t['label']}: " + ("refused the drink." if v == "Refused" else f"drank {v}." if v else "recorded.")
        elif t["ask"] == "pain":
            text = f"Pain check: {v.lower()}." if v else "Pain check done."
        else:
            text = f"{t['label']} done."
        out.append({"time": t["done_at"] or t["due"], "staff": t["done_by"] or "Care chart", "text": text, "tags": ["Care chart"]})
    return out


def attention(resident_ids, now=None):
    """How many chart tiles need attention now (due or late), per resident id."""
    return {rid: sum(t["state"] in ("due", "overdue") for t in tiles(rid, now)) for rid in resident_ids}
