"""Smart task reminders: the care tasks written in each care plan, turned into a "what is due now" list.

No AI here on purpose. The tasks come from data/care_tasks.json (each one names the care plan section it came from),
so a reminder can never be invented. The meal times below are the facility's (fake) routine.
"""
import json
from datetime import date, datetime, time, timedelta

import store
from config import DATA, LOG_DIR

TASKS_DONE = LOG_DIR / "tasks_done.jsonl"
MEAL_TIMES = {"breakfast": "08:00", "lunch": "12:30", "tea": "17:00"}
MEAL_LABEL = {"breakfast": "breakfast", "lunch": "lunch", "tea": "tea"}
AFTER_MEAL_MINUTES = 45
GRACE_MINUTES = 30        # still "due now" for this long after the due time, then "overdue"
MISSED_MINUTES = 180      # after this long the item moves to "earlier today, not ticked"
SOON_MINUTES = 120        # "coming up" window


def _hm(text):
    h, m = text.split(":")
    return time(int(h), int(m))


def load_tasks():
    return json.loads((DATA / "care_tasks.json").read_text())


def occurrences(task):
    """The clock times (as 'HH:MM', with a label) this task is due on a normal day."""
    when = task["when"]
    out = []
    if "every" in when:
        e = when["every"]
        cur = datetime.combine(date.today(), _hm(e["from"]))
        end = datetime.combine(date.today(), _hm(e["to"]))
        while cur <= end:
            out.append((cur.strftime("%H:%M"), ""))
            cur += timedelta(hours=e["hours"])
    for t in when.get("times", []):
        out.append((t, ""))
    for meal in when.get("meals", []):
        out.append((MEAL_TIMES[meal], MEAL_LABEL[meal]))
    if when.get("after_meals"):
        for meal, t in MEAL_TIMES.items():
            due = (datetime.combine(date.today(), _hm(t)) + timedelta(minutes=AFTER_MEAL_MINUTES)).strftime("%H:%M")
            out.append((due, f"after {MEAL_LABEL[meal]}"))
    return sorted(out)


# ---------- what has been ticked off ----------
def _records(day):
    if not TASKS_DONE.exists():
        return []
    out = []
    for line in TASKS_DONE.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("date") == day:
            out.append(r)
    return out


def mark_done(resident_id, task_id, due, staff, at=None, value=""):
    LOG_DIR.mkdir(exist_ok=True)
    at = at or datetime.now()
    rec = {"date": at.date().isoformat(), "resident_id": resident_id, "task_id": task_id, "due": due,
           "by": staff.split(",")[0].strip(), "at": at.strftime("%H:%M")}
    if value:
        rec["value"] = value
    with TASKS_DONE.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def build(resident_ids, now=None):
    """Return every task occurrence for today with a state: done, overdue, due, soon or later.

    `now` is a datetime (a demo clock can be passed in). Items are sorted most urgent first.
    """
    now = now or datetime.now()
    day = now.date().isoformat()
    done = {(r["task_id"], r["due"]): r for r in _records(day)}
    meta = {r["id"]: r for r in store.residents_meta()}
    tasks = load_tasks()
    items = []
    for rid in resident_ids:
        for task in tasks.get(rid, []):
            for due, label in occurrences(task):
                due_dt = datetime.combine(now.date(), _hm(due))
                minutes = (due_dt - now).total_seconds() / 60
                rec = done.get((task["id"], due))
                if rec:
                    state = "done"
                elif minutes < -MISSED_MINUTES:
                    state = "missed"      # long past and not ticked off: kept in the list, but not shouted about
                elif minutes < -GRACE_MINUTES:
                    state = "overdue"
                elif minutes <= 0:
                    state = "due"
                elif minutes <= SOON_MINUTES:
                    state = "soon"
                else:
                    state = "later"
                items.append({"resident_id": rid, "resident": meta[rid]["name"], "room": meta[rid]["room"],
                              "task_id": task["id"], "text": task["text"], "due": due, "label": label,
                              "source": task["source"], "state": state, "done_by": rec["by"] if rec else "",
                              "done_at": rec["at"] if rec else ""})
    order = {"overdue": 0, "due": 1, "soon": 2, "later": 3, "missed": 4, "done": 5}
    items.sort(key=lambda i: (order[i["state"]], i["due"], i["room"]))
    return items


def counts(items):
    out = {"overdue": 0, "due": 0, "soon": 0, "later": 0, "missed": 0, "done": 0}
    for i in items:
        out[i["state"]] += 1
    return out


def attention(resident_ids, now=None):
    """How many tasks need attention now (overdue plus due), per resident id."""
    out = {}
    for i in build(resident_ids, now):
        if i["state"] in ("overdue", "due"):
            out[i["resident_id"]] = out.get(i["resident_id"], 0) + 1
    return out
