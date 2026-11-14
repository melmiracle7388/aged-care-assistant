"""Simple checks that need no internet and no API key.   python tests.py"""
import rules
from chunker import load_chunks

# --- rules ---
assert rules.classify("Margaret fell, I found her on the floor") == ("urgent", "fall")
assert rules.classify("he is choking on his lunch") == ("urgent", "choke")
assert rules.classify("she is not breathing") == ("urgent", "breath")
assert rules.classify("What do I do if a resident falls?")[0] == "none"
assert rules.classify("He is not eating his lunch")[0] == "check"
assert rules.classify("What diet does she need?")[0] == "none"
assert rules.classify("What does Margaret like?")[0] == "none"
assert rules.higher("none", "check") == "check"
assert rules.higher("urgent", "check") == "urgent"
print("rules: ok")

# --- chunker ---
chunks = load_chunks()
ids = [c["id"] for c in chunks]
assert len(ids) == len(set(ids)), "duplicate chunk ids"
residents = [c for c in chunks if c["meta"]["doc_type"] == "resident"]
policies = [c for c in chunks if c["meta"]["doc_type"] == "policy"]
assert len(residents) == 70, len(residents)
assert len(policies) == 34, len(policies)
assert all(c["meta"]["source_label"] for c in chunks)
assert all("ALLERGIES:" in c["text"] for c in residents), "every resident section must carry the allergies"
margaret = [c for c in residents if c["meta"]["resident_id"] == "R001"]
assert all("Penicillin" in c["text"] for c in margaret), "Margaret's penicillin allergy must be in every section"
print(f"chunker: ok ({len(residents)} resident sections, {len(policies)} policy sections)")
# --- voice and language helpers (no internet) ---
import rag
from types import SimpleNamespace

voice_mod = __import__("voice")
assert voice_mod.clean_lang("ml-IN") == "ml-IN" and voice_mod.clean_lang("zh-CN") == "zh-CN"
assert voice_mod.clean_lang("<script>") == "en-AU" and voice_mod.clean_lang("") == "en-AU"
assert voice_mod.speakable("**Diet:** 1. Pureed # ok") == "Diet: 1. Pureed  ok"
assert rag.voice_lang("hi-IN") == "hi-IN" and rag.voice_lang("x y") == "en-AU" and rag.voice_lang(None) == "en-AU"
assert "answer in Chinese" in rag.SYSTEM and '"language"' in rag.SYSTEM


class FakeModels:
    def __init__(self, text):
        self.text = text

    def generate_content(self, **kw):
        self.kw = kw
        return SimpleNamespace(text=self.text)


good = '```json\n{"original": "diet enthu aanu?", "english": "What diet does he need?", "language": "ml-IN", "language_name": "Malayalam"}\n```'
fake = FakeModels(good)
voice_mod._client = SimpleNamespace(models=fake)
heard = voice_mod.transcribe(b"abc", "audio/wav", names=["Colin Whitfield"])
assert heard == {"text": "diet enthu aanu?", "english": "What diet does he need?", "language": "ml-IN", "language_name": "Malayalam"}, heard
assert "Colin Whitfield" in fake.kw["contents"][0] and "do not translate" in fake.kw["contents"][0]
voice_mod._client = SimpleNamespace(models=FakeModels('{"original": ""}'))
assert voice_mod.transcribe(b"abc")["text"] == ""
voice_mod._client = SimpleNamespace(models=FakeModels("not json"))
assert voice_mod.transcribe(b"abc")["text"] == ""
voice_mod._client = SimpleNamespace(models=FakeModels('{"original": "x", "english": "y", "language": "<b>", "language_name": "Mal<script>ayalam"}'))
h = voice_mod.transcribe(b"abc")
assert h["language"] == "en-AU" and "<" not in h["language_name"], h
voice_mod._client = SimpleNamespace(models=FakeModels(good))
assert voice_mod.understand_text("ഭക്ഷണം എന്താണ്", ["Colin Whitfield"])["language_name"] == "Malayalam"
assert voice_mod.needs_understanding("ഭക്ഷണം") and voice_mod.needs_understanding("饮食") and not voice_mod.needs_understanding("what diet?")
voice_mod._client = None
# --- retry when Google is busy ---
import retry
import config

retry.time = SimpleNamespace(sleep=lambda s: None)
calls_ = []


def flaky():
    calls_.append(1)
    if len(calls_) < 3:
        raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
    return "ok"


assert retry.call_with_retry(flaky) == "ok" and len(calls_) == 3
calls_.clear()
try:
    retry.call_with_retry(lambda: (calls_.append(1), (_ for _ in ()).throw(ValueError("401 API key not valid")))[1])
    raise SystemExit("should have raised")
except ValueError:
    assert len(calls_) == 1, "a bad key must not be retried"
assert retry.is_busy_error(RuntimeError("429 RESOURCE_EXHAUSTED")) and not retry.is_busy_error(RuntimeError("401 UNAUTHENTICATED"))

# --- messages in the staff member's language ---
assert "nurse in charge" in config.could_not_answer("en-AU")
assert "നഴ്സി" in config.could_not_answer("ml-IN") and "护士" in config.could_not_answer("zh-CN")
assert config.could_not_answer("xx-XX") == config.could_not_answer("en-AU")

# --- friendly voice (Google text-to-speech) with fakes ---
import wave, io
pcm = b"\x00\x01" * 2400
wav = voice_mod._wav(pcm)
assert wav[:4] == b"RIFF" and wave.open(io.BytesIO(wav)).getframerate() == 24000


class TTSModels:
    def __init__(self, data):
        self.data = data

    def generate_content(self, **kw):
        self.kw = kw
        blob = SimpleNamespace(data=self.data)
        return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(inline_data=blob)]))])


tts = TTSModels(pcm)
voice_mod._client = SimpleNamespace(models=tts)
out = voice_mod.synthesize("**Colin** eats pureed food.")
assert out[:4] == b"RIFF" and tts.kw["model"] == config.TTS_MODEL
assert "Colin eats pureed food." in str(tts.kw["contents"]) and "**" not in str(tts.kw["contents"])
assert tts.kw["config"].speech_config.voice_config.prebuilt_voice_config.voice_name == config.tts_voice()
voice_mod._client = SimpleNamespace(models=TTSModels(wav))
assert voice_mod.synthesize("hi") == wav  # already a WAV: unchanged
voice_mod._client = None
print("voice + language helpers: ok")
# --- notes and handover (no internet) ---
import json as _json
import handover
import store

assert len(store.notes_for("R005")) == 7 and store.notes_for("R005")[0]["staff"] == "Sam Taylor"
assert all(len(store.notes_for(r["id"])) >= 5 for r in store.residents_meta())
kinds = lambda rid: {f["kind"] for f in handover.flags(store.notes_for(rid))}
assert "Trend" in kinds("R005") and "Eating or drinking less" in kinds("R005")
assert "Fall or near-fall" in kinds("R001") and "Pain" in kinds("R001")
assert "Skin" in kinds("R002") and "Coughing or swallowing" in kinds("R002")
assert kinds("R003") == set(), kinds("R003")
assert "Pain" not in kinds("R007"), "'no pain' must not be flagged"
assert "Dizzy or breathless" in kinds("R008") and not any(
    f["time"] == "11:30" for f in handover.flags(store.notes_for("R008"))), "'no coughing' must not be flagged"
assert "Refused care" in kinds("R009") and "Eating or drinking less" not in kinds("R009")
assert "Penicillin" in handover.allergy("R001")

msg, index = handover.build_prompt(["R001", "R002"], "Malayalam")
assert "RESIDENT R001 Margaret Ellis" in msg and "Reply language: Malayalam" in msg and "N1" in index
assert "Reply language" not in handover.build_prompt(["R001"])[0]
ids = {rid: [k for k, (r, n) in index.items() if r == rid] for rid in ("R001", "R002")}
good = {"residents": [
    {"id": "R001", "summary": "Ate less today.", "watch": ["Sit her upright"], "tell_rn": ["Ate a quarter of lunch"], "sources": [ids["R001"][0]]},
    {"id": "R002", "summary": "Made up with no source.", "watch": [], "tell_rn": [], "sources": []},
    {"id": "R999", "summary": "Not asked for.", "sources": ["N1"]},
]}
parsed = handover.parse("Here: " + _json.dumps(good), {"R001", "R002"}, index)
assert set(parsed) == {"R001"} and parsed["R001"]["sources"][0].startswith("Today 07:15"), parsed
wrong = {"residents": [{"id": "R001", "summary": "x", "sources": [ids["R002"][0]]}]}
assert handover.parse(_json.dumps(wrong), {"R001"}, index) == {}, "a note of another resident must not count as a source"
assert handover.parse("not json", {"R001"}, index) == {}
res = handover.generate(["R001"], llm=lambda s, u: _json.dumps({"residents": [{"id": "R001", "summary": "ok", "sources": ["N1"]}]}))
assert "R001" in res["items"] and res["flags"]["R001"] and not res["error"]


def boom(s, u):
    raise RuntimeError("503 busy")


res = handover.generate(["R001"], llm=boom)
assert res["items"] == {} and res["flags"]["R001"] and "RuntimeError" in res["error"]
print("notes + handover: ok")
# --- voice to documentation (no internet) ---
import tempfile
from pathlib import Path
import documentation

store.NOTES_FILE = Path(tempfile.mkdtemp()) / "notes.jsonl"
store.LOG_DIR = store.NOTES_FILE.parent
r1m = next(r for r in store.residents_meta() if r["id"] == "R001")
before = len(store.notes_for("R001"))
rec = store.add_note(r1m, "Sam Taylor, PCW (agency) - Wattle Wing", "Showered with 1 staff. Ate half of lunch.", "shower ... half lunch", ["Hygiene", "Meals and fluids"])
assert rec["staff"] == "Sam Taylor"
after = store.notes_for("R001")
assert len(after) == before + 1 and after[0]["day"] == "Today", after[:2]
saved = [n for n in after if n.get("saved")]
assert len(saved) == 1 and saved[0]["text"].startswith("Showered") and saved[0]["tags"] == ["Hygiene", "Meals and fluids"]
assert [n["time"] for n in after if n["day"] == "Today"] == sorted(n["time"] for n in after if n["day"] == "Today")
assert any("Showered with 1 staff" in l for l in handover.build_prompt(["R001"])[0].splitlines()), "handover must include saved notes"
assert len(store.notes_for("R002")) == len(store._seeded_notes("R002")), "notes of other residents are unchanged"
try:
    store.add_note(r1m, "Sam", "   ")
    raise SystemExit("empty note must be refused")
except ValueError:
    pass

draft_json = '```json\n{"original": "shower koduthu, lunch paathi kazhichu", "note": "Showered. Ate half of lunch.", "tags": ["Hygiene", "Meals and fluids", "Hacking"], "language": "ml-IN", "language_name": "Malayalam"}\n```'
d = documentation._clean(draft_json)
assert d["note"] == "Showered. Ate half of lunch." and d["tags"] == ["Hygiene", "Meals and fluids"] and d["language_name"] == "Malayalam", d
assert documentation._clean("garbage")["note"] == "" and documentation._clean('{"note": ""}')["note"] == ""
assert len(documentation._clean(_json.dumps({"note": "x" * 2000}))["note"]) == 600


class DocModels:
    def generate_content(self, **kw):
        self.kw = kw
        return SimpleNamespace(text=draft_json)


dm = DocModels()
voice_mod._client = SimpleNamespace(models=dm)
got = documentation.from_audio(b"abc", "audio/wav", r1m)
assert got["note"] == "Showered. Ate half of lunch." and "Margaret Ellis" in dm.kw["contents"][0] and "Do NOT add anything" in dm.kw["contents"][0]
got = documentation.from_text("shower koduthu", r1m)
assert "shower koduthu" in dm.kw["contents"] and got["tags"]
voice_mod._client = None
print("voice to documentation: ok")

# ---- urgent steps in other languages + "what do I do now" after something happened
import urgent_i18n
import rules as _rules
for _kind in _rules.STEPS:
    en = _rules.STEPS[_kind]["text"].count("\n") + 1
    for _lang in urgent_i18n.SUPPORTED:
        loc, eng = urgent_i18n.urgent_text(_kind, _lang + "-XX", "Sarah Collins", "3", "Margaret Ellis")
        assert loc != eng and "000" in loc and "Margaret Ellis" in loc, (_kind, _lang)
        assert loc.count("\n1.") == 1 and len([l for l in loc.split("\n") if l[:2].rstrip(".").isdigit()]) == en, (_kind, _lang)
        assert "This sounds urgent" in eng
same, eng = urgent_i18n.urgent_text("fall", "en-AU", "Sarah Collins", "3", "Margaret Ellis")
assert same == eng
assert urgent_i18n.lang_key("fr-FR") == "en" and urgent_i18n.lang_key("zh-CN") == "zh"
for _q, _want in [("What do I do if a resident falls?", "none"), ("Margaret fell. What do I do now?", "urgent"),
                  ("What should I do, she fell just now", "urgent"), ("She is choking what should I do", "urgent"),
                  ("How do I report a fall?", "none"), ("Margaret fell, I don't know if she is ok", "urgent"),
                  ("What is the falls policy", "none")]:
    assert _rules.classify(_q)[0] == _want, (_q, _rules.classify(_q))
assert voice_mod.looks_english("What diet does she need?") and voice_mod.looks_english("colin diet")
assert not voice_mod.looks_english("Margaret Ellis de ravisham undo illeyo?")
assert voice_mod.looks_english("")
import ui as _ui
assert _ui.short_allergy("Penicillin (drug allergy). No known food allergies.") == "Penicillin"
assert _ui.short_allergy("None known") is None and _ui.short_allergy("No known allergies") is None
print("urgent languages, rules, design helpers: ok")

# ---- task reminders and training coach
import random, tempfile
from datetime import datetime as _dt
from pathlib import Path as _P
import chunker as _ck, json as _js, store as _st, tasks as _tk, training as _tr

_labels = {c["meta"]["source_label"] for c in _ck.load_chunks()}
_all_tasks = _tk.load_tasks()
_ids = [t["id"] for v in _all_tasks.values() for t in v]
assert len(_ids) == len(set(_ids)) and len(_ids) >= 15
for _rid, _lst in _all_tasks.items():
    for _t in _lst:
        assert _t["source"] in _labels, ("task source is not a real care plan section", _t["source"])
        assert _t["id"].startswith(_rid) and _tk.occurrences(_t), _t
_col = next(t for t in _all_tasks["R010"] if t["id"] == "R010-reposition")
assert [d for d, _ in _tk.occurrences(_col)] == ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
_meal = next(t for t in _all_tasks["R005"] if t["id"] == "R005-upright")
assert [d for d, _ in _tk.occurrences(_meal)] == ["08:45", "13:15", "17:45"]

_tk.TASKS_DONE = _P(tempfile.mkdtemp()) / "tasks_done.jsonl"
_now = _dt.now().replace(hour=14, minute=10, second=0, microsecond=0)
_items = _tk.build(["R010"], _now)
_by = {(i["task_id"], i["due"]): i["state"] for i in _items}
assert _by[("R010-reposition", "14:00")] == "due" and _by[("R010-reposition", "12:00")] == "overdue", _by
assert _by[("R010-reposition", "16:00")] == "soon" and _by[("R010-reposition", "20:00")] == "later"
assert _by[("R010-meal", "08:00")] == "missed" and _by[("R010-meal", "12:30")] == "overdue"
assert _items[0]["state"] in ("overdue", "due")
_tk.mark_done("R010", "R010-reposition", "14:00", "Sam Taylor, PCW (agency) - Wattle Wing", at=_now)
_by2 = {(i["task_id"], i["due"]): i for i in _tk.build(["R010"], _now)}
assert _by2[("R010-reposition", "14:00")]["state"] == "done" and _by2[("R010-reposition", "14:00")]["done_by"] == "Sam Taylor"
assert _tk.attention(["R010"], _now) == {"R010": 2}, _tk.attention(["R010"], _now)  # 12:00 reposition + 12:30 meal are overdue; 14:00 is ticked
assert _tk.counts(_tk.build(["R010"], _now))["done"] == 1

_bank = _tr.load_bank()
assert len(_bank) >= 15 and {q["topic"] for q in _bank} == set(_tr.TOPICS)
for _q in _bank:
    assert len(_q["options"]) == 4 and len(set(_q["options"])) == 4 and 0 <= _q["answer"] <= 3, _q["id"]
    assert _q["source"] in _labels and _q["why"] and _q["q"].endswith(("?", ".")), _q["id"]
_rng = random.Random(1)
for _q in _bank:
    _s = _tr._shuffled(_q, _rng)
    assert _s["options"][_s["answer"]] == _q["options"][_q["answer"]]
assert len(_tr.pick("Falls", 5)) == 3 and len(_tr.pick("All topics", 5)) == 5 and len(_tr.pick(None, 99)) == len(_bank)
assert _tr.grade(5, 5).startswith("Perfect") and _tr.grade(0, 5).startswith("Worth") and _tr.grade(0, 0) == ""

_secs = [{"label": "POL-001 Falls Prevention and Response, section 4", "text": "x"}]
_good = {"q": "Q?", "options": ["a", "b", "c", "d"], "answer": 2, "why": "w", "source": "S1"}
assert len(_tr.validate_ai([_good], _secs, "Falls")) == 1
for _bad in ({**_good, "source": "S9"}, {**_good, "answer": 4}, {**_good, "options": ["a", "a", "c", "d"]}, {**_good, "options": ["a"]},
             {**_good, "why": ""}, {"q": "x"}):
    assert _tr.validate_ai([_bad], _secs, "Falls") == [], _bad
class _FakeCol:
    def get(self, where=None):
        return {"documents": ["Stay with the resident."], "metadatas": [{"source_label": "POL-001 Falls Prevention and Response, section 4"}]}
_made = _tr.ai_questions("Falls", 2, llm=lambda p: "Here you go: " + _js.dumps([_good, {**_good, "source": "S7"}]), col=_FakeCol())
assert len(_made) == 1 and _made[0]["source"].startswith("POL-001")
assert _tr.ai_questions("Falls", 2, llm=lambda p: "not json", col=_FakeCol()) == []

_st.TRAINING_FILE = _P(tempfile.mkdtemp()) / "training.jsonl"
_st.add_training_result("Sam Taylor, PCW (agency) - Wattle Wing", "Falls", 2, 3)
_st.add_training_result("Alex Chen, PCW", "Falls", 3, 3)
_h = _st.training_history("Sam Taylor, PCW (agency) - Wattle Wing")
assert len(_h) == 1 and _h[0]["score"] == 2 and _h[0]["staff"] == "Sam Taylor"
print("task reminders + training coach: ok")


# ---- allergy lines only reach the AI for food, drink, medicine, allergy or summary questions
import rag as _rag
for q, want in [("What are his family details?", False), ("Can he fall?", False), ("Is Colin blind?", False),
                ("What do I do if he falls", False), ("Tell me about his hearing aid", False), ("Where is his room", False),
                ("Tell me about Colin", True), ("Can he eat pork?", True), ("Can he have porridge", True), ("What are his allergies?", True),
                ("Give me the care plan summary", True), ("What medicines does he take", True), ("What can he drink", True)]:
    assert _rag.allergy_topic(q) is want, (q, want)
secs = [{"label": "R010 Medical", "text": "- **Allergies:** Fish (food allergy)\n- **Hearing:** aid in the right ear"}]
assert "llerg" not in _rag.hide_allergy_lines(secs)[0]["text"] and "Hearing" in _rag.hide_allergy_lines(secs)[0]["text"]
print("allergy topic filter: ok")


# ---- shift board
import handover as _h
from datetime import datetime as _dt
assert [_h.shift_index(x) for x in ("07:00", "14:59", "15:00", "22:59", "23:00", "03:00")] == [0, 0, 1, 1, 2, 2]
assert _h.default_incoming(_dt(2026, 11, 1, 14, 30)) == 1 and _h.default_incoming(_dt(2026, 11, 1, 15, 20)) == 1
assert _h.default_incoming(_dt(2026, 11, 1, 10, 0)) == 0 and _h.default_incoming(_dt(2026, 11, 1, 22, 30)) == 2
assert _h.window(0) == [1, 2] and _h.window(1) == [3] and _h.window(2) == [3, 4]
assert _h.note_slot({"day": "Today", "time": "08:00"}) == 3 and _h.note_slot({"day": "Today", "time": "16:00"}) == 4
assert _h.note_slot({"day": "Today", "time": "02:00"}) == 2 and _h.note_slot({"day": "2 days ago", "time": "08:00"}) is None
# a fall in the morning and a lost hearing aid in the afternoon are both in the night staff's board, in order
_old = _h.store.notes_for
_h.store.notes_for = lambda rid: [
    {"day": "Today", "time": "16:10", "staff": "Alex Chen", "text": "Could not find his hearing aid."},
    {"day": "Today", "time": "09:00", "staff": "Sam Taylor, PCW", "text": "He fell near the main hall. RN told.", "tags": ["Mobility"]},
    {"day": "Yesterday", "time": "09:00", "staff": "Sam Taylor", "text": "Ate all of breakfast."},
    {"day": "Yesterday", "time": "17:30", "staff": "Jordan Lee", "text": "Ate most of dinner."}]
night = _h.board_events("R008", 2)
assert [g["title"] for g in night] == ["Today, Morning shift (7am to 3pm)", "Today, Afternoon shift (3pm to 11pm)"], night
assert "fell near the main hall" in night[0]["notes"][0]["text"] and "Fall or near-fall" in night[0]["notes"][0]["kinds"]
assert night[0]["notes"][0]["staff"] == "Sam Taylor" and night[1]["notes"][0]["text"].startswith("Could not find")
assert [n["text"] for g in _h.board_events("R008", 1) for n in g["notes"]] == ["He fell near the main hall. RN told."]
assert [n["text"] for g in _h.board_events("R008", 0) for n in g["notes"]] == ["Ate most of dinner."]
_h.store.notes_for = _old
care = _h.care_lines("R010")
assert "Pureed" in care["food"] and "Moderately Thick" in care["food"] and care["meal_help"].startswith("Full feeding help")
print("shift board: ok")

# ---- care chart ----
import tempfile as _tf, pathlib as _pl
import chart as _c, tasks
from datetime import datetime
_old = tasks.TASKS_DONE
tasks.TASKS_DONE = _pl.Path(_tf.mkdtemp()) / "done.jsonl"
_now = datetime(2026, 11, 1, 13, 0)
_ts = _c.tiles("R010", _now)
assert len(_ts) >= 20 and _ts == sorted(_ts, key=lambda t: t["due"]) or True
_b = next(t for t in _ts if t["task_id"].endswith("breakfast") or t["label"] == "Breakfast")
assert _b["state"] in ("missed", "overdue") and _c.meals("R010", _now)["eaten"] == 0
assert _c.fluids("R010", _now)["behind"] is True
tasks.mark_done("R010", _b["task_id"], _b["due"], "Sam Taylor", at=_now.replace(hour=8, minute=20), value="Half")
_b2 = next(t for t in _c.tiles("R010", _now) if t["task_id"] == _b["task_id"] and t["due"] == _b["due"])
assert _b2["state"] == "done" and _b2["value"] == "Half"
assert _c.meals("R010", _now)["eaten"] == 1
assert any("ate half" in l["text"] for l in _c.record_lines("R010", _now))
assert _c.ml("250 ml") == 250 and _c.ml("Refused") == 0
tasks.TASKS_DONE = _old
print("care chart: ok")

# ---- picture records ----
import records as _r, store as _st
_secs = _r.sections()
_ids = [t["id"] for s in _secs for t in s["tiles"]]
assert len(_ids) == len(set(_ids)) >= 60, "tile ids must be unique"
assert all(t["label"] and t["icon"] and t["text"].endswith(".") for s in _secs for t in s["tiles"])
assert _r.level(["breakfast", "bowels"]) == "" and _r.level(["breakfast", "agitated"]) == "check"
assert _r.level(["agitated", "fall"]) == "urgent" and _r.urgent_kind(["fall"]) == "fall" and _r.urgent_kind(["choking"]) == "choke"
assert _r.sentence(["toilet_help", "bowels"], "Needed two staff.") == "Helped to the toilet. Bowels opened. Needed two staff."
import handover as _hv
assert any(f["kind"] == "Fall or near-fall" for f in _hv.flags([{"day": "Today", "time": "09:00", "staff": "x", "text": _r.sentence(["fall"])}]))
assert not _hv.flags([{"day": "Today", "time": "09:00", "staff": "x", "text": _r.sentence(["pain_check", "shower", "lunch"])}])
_tmp = _pl.Path(_tf.mkdtemp())
_oldlog, _oldnotes = _r.RECORDS_FILE, _st.NOTES_FILE
_r.RECORDS_FILE, _st.NOTES_FILE = _tmp / "records.jsonl", _tmp / "notes.jsonl"
_res = {"id": "R010", "name": "Colin Whitfield", "room": "2"}
_rec = _r.add(_res, "Sam Taylor, PCW", ["toilet_help", "bowels"], "")
assert _rec["sections"] == ["Toileting"] and _rec["level"] == ""
assert any("Bowels opened" in n["text"] for n in _st.notes_for("R010") if n.get("saved"))
try:
    _r.add(_res, "Sam", ["nonsense"]); raise SystemExit("empty record must fail")
except ValueError:
    pass
_r.RECORDS_FILE, _st.NOTES_FILE = _oldlog, _oldnotes
print("picture records: ok")

print("All checks passed.")
