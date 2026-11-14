"""CareAsk demo screen (Streamlit). Fictional data only.

Run with:  streamlit run app.py
"""
import html
import re
from datetime import datetime

import streamlit as st

import config
import documentation
import handover
import rag
import voice
import rules
import store
import tasks
import chart
import records
import training
import ui
import urgent_i18n

st.set_page_config(page_title="CareAsk (demo)", page_icon="💬", layout="centered")
ui.inject_css()


def live(run_every):
    """Auto-refresh a section every few seconds (needs a recent Streamlit; otherwise no refresh)."""
    def wrap(fn):
        frag = getattr(st, "fragment", None)
        return frag(run_every=run_every)(fn) if frag else fn
    return wrap


def alert_status(al):
    if al is None:
        return "", "info"
    if al["status"] == "ack":
        return f"RN {config.RN_NAME} is on the way.", "success"
    return f"Alert sent at {al['time']}. Waiting for the RN to confirm.", "warning"


# ---------------------------------------------------------------- RN phone
@live(5)
def rn_view():
    st.markdown(f"## Alerts for RN {config.RN_NAME}")
    st.caption("Pretend RN phone. New alerts from care staff appear here and refresh every 5 seconds.")
    alerts = list(reversed(store.all_alerts()))
    if not alerts:
        st.info("No alerts yet. Switch to the care staff phone, open a resident and tap Emergency.")
    for a in alerts:
        with st.container(border=True):
            tag, cls = ("Urgent", "urgent") if a["level"] == "urgent" else ("Please check", "check")
            st.markdown(f'<span class="rnhead {cls}">{tag}</span> &nbsp;<span style="color:#4A6165">{a["time"]}</span>', unsafe_allow_html=True)
            st.markdown(f"### Room {a['room']}: {a['resident']}")
            st.write(a["what"])
            st.caption(f"Reported by: {a['by']}")
            if a["steps"]:
                st.caption(a["steps"])
            if a["status"] == "ack":
                st.success("You confirmed. The care staff phone shows you are on the way.")
            elif st.button("I'm on my way", key=f"ack_{a['id']}", type="primary", use_container_width=True):
                store.ack_alert(a["id"])
                st.rerun()


# ---------------------------------------------------------------- care staff
def new_alert(level, resident, what, steps, staff):
    return store.add_alert(level, resident, what, steps, staff)


CONDITIONAL = re.compile(r"\b(if|in case|whenever)\b")
# "can he fall", "is a fall possible", "how do I prevent falls": questions about risk, not something happening
POSSIBLE = re.compile(r"\b(can(?!['\u2019]t|not)|could(?! not|n['\u2019]t)|might|may|possible|possibility|likely|chance|risk|prevent|avoid|stop)\b")


def other_resident_named(q, english, resident):
    """The resident (from the list) named in the question when it is NOT the open page's resident, else None."""
    text = f"{q} {english or ''}".lower()
    def named(r):
        return any(re.search(rf"\b{re.escape(p.lower())}\b", text) for p in r["name"].split() if len(p) > 2)
    if named(resident):
        return None
    for r in store.residents_meta():
        if r["id"] != resident["id"] and named(r):
            return r
    return None


def handle_question(q, resident, staff, voice_q=False, heard=None, calm=False, echo=True):
    """Rules first, then the AI. The AI can only raise the level, never lower it.

    `heard` (from voice.transcribe) holds the plain-English meaning and language of the question.
    """
    first = resident["name"].split()[0]
    msgs = st.session_state.msgs.setdefault(resident["id"], [])
    history, last_q = [], None  # recent questions and answers, so follow-ups make sense
    for m in msgs:
        if m["role"] == "user":
            last_q = m["text"]
        elif last_q and m.get("kind") in ("info", "check"):
            history.append((last_q, m["text"][:400]))
            last_q = None
    if echo:
        msgs.append({"role": "user", "text": q})

    names = [r["name"] for r in store.residents_meta()]
    if heard is None and (voice.needs_understanding(q) or not voice.looks_english(q)):  # another language, script or romanised
        try:
            heard = voice.understand_text(q, names)
        except Exception as err:
            st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
    english = (heard or {}).get("english") or None
    lang_name = (heard or {}).get("language_name") or None

    guess = rag.script_language(q)  # works even when the AI was busy: the script itself tells the language
    if not lang_name and guess:
        lang_name = guess[1]
    ulang = (heard or {}).get("language") or (guess[0] if guess else "en-AU")

    other = other_resident_named(q, english, resident)
    if other:  # the question is about someone else: say so, never answer with this resident's information
        on_roster = other["id"] in store.roster().get(staff, [])
        lv, _ = rules.classify(english or q)
        lv = rules.higher(lv, rules.classify(q)[0])
        text, text_en, btn = urgent_i18n.wrong_resident(ulang, resident["name"].split()[0], other["name"].split()[0],
                                                        on_roster, lv != "none")
        msgs.append({"role": "assistant", "kind": "switch", "text": text, "english": "" if text == text_en else text_en,
                     "lang": urgent_i18n.LANG_TAG[urgent_i18n.lang_key(ulang)], "other_id": other["id"], "btn": btn,
                     "pending": q, "on_roster": on_roster, "urgent_hint": lv != "none"})
        store.log_search(staff, resident["id"], q, "none", [], True)
        return

    level, kind = rules.classify(q)
    if english:  # the red-flag rules also read the plain-English meaning
        level2, kind2 = rules.classify(english)
        if rules.higher(level, level2) != level:
            level, kind = level2, kind2
    res = None
    if level != "urgent":
        with st.spinner("Checking the care plan and policies..."):
            try:
                extra = {"english": english, "lang_name": lang_name, "lang_tag": (heard or {}).get("language") or (guess[0] if guess else None),
                         "history": history, "smart": bool(st.session_state.get("smart"))}
                res = rag.answer(q, resident, talk=True, **extra) if voice_q else rag.answer(q, resident, **extra)
            except Exception as err:  # no key, no internet, quota used up, database not built...
                st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
                res = {"found": False, "answer": config.could_not_answer((heard or {}).get("language")),
                       "sources": [], "urgency": "none", "urgent_type": "none",
                       "language": (heard or {}).get("language") or "en-AU"}
        if urgent_i18n.lang_key(res.get("language")) != "en" and urgent_i18n.lang_key(ulang) == "en":
            ulang = res["language"]  # the AI recognised the language even though the first check did not
        if res["urgency"] != "none":
            ai_level = res["urgency"]
            if calm and ai_level == "urgent":  # the staff member said nothing is happening now
                ai_level = "check" if level == "check" else "none"
            elif ai_level == "urgent" and level != "urgent" and (CONDITIONAL.search((english or q).lower())
                                                            or POSSIBLE.search((english or q).lower())):
                # "what do I do IF he falls": the rules saw no emergency and the wording is conditional, so ask first
                lang = (res.get("language") or ulang)
                qtext, _, _ = urgent_i18n.now_text(lang, first)
                kind_ = res["urgent_type"] if res["urgent_type"] != "none" else "other"
                msgs.append({"role": "assistant", "kind": "confirm", "text": qtext, "lang": urgent_i18n.LANG_TAG[urgent_i18n.lang_key(lang)],
                             "pending": q, "ukind": kind_, "english": english or "", "lang_name": lang_name or "", "ulang": lang})
                store.log_search(staff, resident["id"], q, "check", [], True)
                return
            level = rules.higher(level, ai_level)
            if level == "urgent":
                kind = res["urgent_type"] if res["urgent_type"] != "none" else "other"

    sources = []
    if level == "urgent":
        steps = rules.STEPS.get(kind, rules.STEPS["other"])
        aid = new_alert("urgent", resident, q, "Steps given to staff:\n" + steps["text"], staff)
        text, text_en = urgent_i18n.urgent_text(kind, ulang, config.RN_NAME, resident["room"], resident["name"])
        same = text == text_en
        msgs.append({"role": "assistant", "kind": "urgent", "text": text, "sources": [steps["source"]], "alert_id": aid,
                     "autoplay": voice_q, "lang": urgent_i18n.LANG_TAG[urgent_i18n.lang_key(ulang)],
                     "english": "" if same else text_en})
        sources = [steps["source"]]
    elif level == "check":
        lang = (res or {}).get("language") or ulang
        lead = (res["answer"] + "\n\n") if res and res["found"] else ""
        tail, tail_en = urgent_i18n.check_text(lang, first)
        text = lead + tail
        src = (res["sources"] if res and res["found"] else []) + ["POL-006 Reporting Changes in a Resident's Condition, section 3"]
        english = (res or {}).get("english", "")
        if english and tail != tail_en:
            english = english + "\n\n" + tail_en
        msgs.append({"role": "assistant", "kind": "check", "text": text, "sources": src, "pending": q,
                     "timing": (res or {}).get("timing"), "lang": lang,
                     "english": english, "autoplay": voice_q})
        sources = src
    else:
        kind_ = "info" if res["found"] else "notfound"
        msgs.append({"role": "assistant", "kind": kind_, "text": res["answer"], "sources": res["sources"],
                     "timing": res.get("timing"), "lang": res.get("language", "en-AU"),
                     "english": res.get("english", ""), "spoken": res.get("spoken", ""), "autoplay": voice_q,
                     "not_recorded": res.get("not_recorded", False), "followups": res.get("followups", [])})
        sources = res["sources"]

    store.log_search(staff, resident["id"], q, level, sources, bool(res["found"]) if res else True)

    if voice_q and level != "urgent" and config.google_tts_on():
        msgs[-1]["autoplay"] = False  # the friendly voice is prepared next, and plays by itself
        st.session_state.pending_tts = (resident["id"], len(msgs) - 1)


def confirm_now(m, resident, staff, yes):
    """The staff member answered 'is something happening right now?'."""
    m["resolved"] = "yes" if yes else "no"
    if yes:
        msgs = st.session_state.msgs[resident["id"]]
        steps = rules.STEPS.get(m["ukind"], rules.STEPS["other"])
        aid = new_alert("urgent", resident, m["pending"], "Steps given to staff:\n" + steps["text"], staff)
        text, text_en = urgent_i18n.urgent_text(m["ukind"], m["ulang"], config.RN_NAME, resident["room"], resident["name"])
        msgs.append({"role": "assistant", "kind": "urgent", "text": text, "sources": [steps["source"]], "alert_id": aid,
                     "autoplay": False, "lang": m["lang"], "english": "" if text == text_en else text_en})
    else:
        heard = {"text": m["pending"], "english": ("General question, nothing is happening now: " + m["english"]) if m["english"] else "",
                 "language": m["ulang"], "language_name": m["lang_name"]}
        handle_question(m["pending"], resident, staff, heard=heard if m["english"] else None, calm=True, echo=False)


def ask_rn(resident, staff):
    first = resident["name"].split()[0]
    msgs = st.session_state.msgs.setdefault(resident["id"], [])
    aid = new_alert("check", resident, f"Staff member is not sure and needs the RN's advice about {resident['name']}.",
                    "Not urgent. Staff member asked for advice.", staff)
    msgs.append({"role": "user", "text": "I am not sure. Please ask the RN."})
    msgs.append({
        "role": "assistant", "kind": "check", "alert_id": aid,
        "text": f"I have sent a message to RN {config.RN_NAME} for Room {resident['room']}. Stay with {first} until the RN replies.",
        "sources": ["POL-006 Reporting Changes in a Resident's Condition, section 4"],
    })
    store.log_search(staff, resident["id"], "(asked the RN)", "check", [], True)


def render_message(i, m, resident, staff):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(f'<div class="ubub">{html.escape(m["text"])}</div>', unsafe_allow_html=True)
        return
    with st.chat_message("assistant"):
        kind = m["kind"]
        box = {"urgent": "urgent", "check": "chk", "confirm": "chk"}.get(kind, "info")
        holder = st.container(border=True, key=f"{box}_{resident['id']}_{i}")
        with holder:
            if kind == "urgent":
                st.markdown('<div class="banner urgent">Urgent: the RN has been alerted</div>', unsafe_allow_html=True)
            elif kind == "check":
                st.markdown('<div class="banner check">Tell the RN</div>', unsafe_allow_html=True)
            if m.get("not_recorded"):
                st.markdown('<span class="chip warn">Not listed in the care plan</span>', unsafe_allow_html=True)
            st.write(m["text"])
            if kind == "switch":
                if m.get("english"):
                    with st.expander("English original (to check the translation)"):
                        st.write(m["english"])
                if m.get("on_roster"):
                    if st.button(m["btn"], key=f"sw_{resident['id']}_{i}", type="primary", use_container_width=True):
                        st.session_state.auto_ask = (m["other_id"], m["pending"])
                        st.session_state.sel = m["other_id"]
                        st.session_state.chat_open = True
                        st.session_state.panel = None
                        st.rerun()
                return
            if kind == "confirm":
                if m.get("resolved"):
                    st.caption("Answered." if m["resolved"] == "no" else "RN alerted.")
                else:
                    _, yes_l, no_l = urgent_i18n.now_text(m.get("ulang"), resident["name"].split()[0])
                    if st.button(yes_l, key=f"cyes_{resident['id']}_{i}", type="primary", use_container_width=True):
                        confirm_now(m, resident, staff, True)
                        st.rerun()
                    if st.button(no_l, key=f"cno_{resident['id']}_{i}", use_container_width=True):
                        confirm_now(m, resident, staff, False)
                        st.rerun()
                return
            if m.get("sources"):
                st.markdown(ui.source_row(m["sources"]), unsafe_allow_html=True)
            if m.get("english"):
                with st.expander("English original (to check the translation)"):
                    st.write(m["english"])
            if kind in ("info", "check"):
                st.markdown(f'<div class="foot">{urgent_i18n.confirm_text(m.get("lang"))}</div>', unsafe_allow_html=True)
            if m.get("audio"):
                voice.play(m["audio"], autoplay=m.pop("autoplay_audio", False))
            else:
                voice.speak_button(m.get("spoken") or m["text"], m.get("lang", "en-AU"), auto=m.pop("autoplay", False))
            t = m.get("timing")
            if t:
                st.caption(f"Answered in {t['search'] + t['ai']:.1f} s")
            if m.get("followups") and st.session_state.msgs[resident["id"]][-1] is m:
                with st.container(key=f"nf_fu_{resident['id']}_{i}"):  # same look as the topic buttons
                    for n, f in enumerate(m["followups"]):
                        if st.button(f, key=f"fu_{resident['id']}_{i}_{n}", use_container_width=True):
                            handle_question(f, resident, staff)
                            st.rerun()

            aid = m.get("alert_id")
            if aid:
                text, tone = alert_status(store.get_alert(aid))
                getattr(st, tone)(text)
            elif kind == "check":
                if st.button("Notify the RN now", key=f"notify_{resident['id']}_{i}", use_container_width=True):
                    new_id = new_alert("check", resident, m["pending"], "Not urgent. Please come and assess when you can.", staff)
                    m["alert_id"] = new_id
                    st.rerun()
            elif kind == "notfound":
                first = resident["name"].split()[0]
                if st.session_state.msgs[resident["id"]][-1] is m:  # help only under the newest answer
                    st.markdown(f'<div class="foot">Not in the documents. You could ask about one of these, or ask the RN:</div>',
                                unsafe_allow_html=True)
                    topics = [n for n in store.resident_sections(resident["id"]) if n not in ("Basics", "Overview")]
                    with st.container(key=f"nf_{resident['id']}_{i}"):
                        cols = st.columns(2)
                        for n, topic in enumerate(topics):
                            if cols[n % 2].button(topic, key=f"nfb_{resident['id']}_{i}_{n}", use_container_width=True):
                                handle_question(f"Tell me about {first}'s {topic.lower()}", resident, staff)
                                st.rerun()
                if st.button("Ask the RN about this", key=f"askrn_{resident['id']}_{i}", type="primary", use_container_width=True):
                    ask_rn(resident, staff)
                    st.rerun()


def note_entry(resident, staff, expanded=False):
    """Speak or type a note. The app drafts a clean care note; the worker checks it, then saves."""
    rid = resident["id"]
    drafts = st.session_state.setdefault("note_drafts", {})
    st.session_state.setdefault("note_mic_n", 0)
    st.session_state.setdefault("note_v", 0)
    if st.session_state.get("note_flash"):
        st.success(st.session_state.pop("note_flash"))

    draft = drafts.get(rid)
    if draft is None:
        problem = st.session_state.pop("note_problem", "")
        if problem:
            st.warning(problem)
        with st.expander("Add a note: speak or type", expanded=bool(problem) or expanded):
            audio = st.audio_input("Speak your note (any language)", key=f"note_mic_{st.session_state.note_mic_n}")
            if audio is not None:
                st.session_state.note_mic_n += 1
                d = None
                try:
                    with st.spinner("Listening and writing the note..."):
                        d = documentation.from_audio(audio.getvalue(), audio.type or "audio/wav", resident)
                except Exception as err:
                    st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
                if d and d["note"]:
                    st.session_state.note_v += 1
                    drafts[rid] = {**d, "v": st.session_state.note_v}
                else:
                    st.session_state.note_problem = "I could not hear a clear note. Please try again, or type it."
                st.rerun()
            typed = st.text_area("Or type your note", key=f"note_text_{rid}", height=100)
            if st.button("Check my note", key=f"note_check_{rid}", use_container_width=True) and typed.strip():
                d = None
                try:
                    with st.spinner("Writing the note..."):
                        d = documentation.from_text(typed, resident)
                except Exception as err:
                    st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
                if d and d["note"]:
                    st.session_state.note_v += 1
                    drafts[rid] = {**d, "v": st.session_state.note_v}
                else:
                    st.session_state.note_problem = "The note could not be written right now. Please try again."
                st.rerun()
        return

    with st.container(border=True):
        st.markdown("**Check this note before saving**")
        if draft["original"] and not draft["language"].startswith("en"):
            st.caption("You said: " + draft["original"])
        text = st.text_area("Note (you can change it)", value=draft["note"], key=f"note_edit_{rid}_{draft['v']}", height=120)
        if draft["tags"]:
            st.caption("Type: " + ", ".join(draft["tags"]))
        level, _ = rules.classify(text)
        kinds = sorted({f["kind"] for f in handover.flags([{"day": "Today", "time": "", "staff": "", "text": text}])})
        if level == "urgent":
            st.error("This sounds urgent. If it is happening now, use the Emergency button at the top and alert the RN. Do not wait to save a note. If it already happened, the RN must be told too.")
        elif kinds:
            st.warning("This note mentions: " + ", ".join(kinds) + ". Consider telling the RN.")
        st.caption("Only what you said is written. Nothing is saved until you press Save.")
        save, tell, drop = st.columns(3)
        if save.button("Save note", type="primary", key=f"note_save_{rid}", disabled=not text.strip(), use_container_width=True):
            store.add_note(resident, staff, text, original=draft["original"], tags=draft["tags"])
            drafts.pop(rid, None)
            st.session_state.note_flash = "Note saved."
            st.rerun()
        if (kinds or level == "urgent") and tell.button("Save and tell the RN", key=f"note_tell_{rid}", disabled=not text.strip(),
                                                         use_container_width=True):
            store.add_note(resident, staff, text, original=draft["original"], tags=draft["tags"])
            new_alert("check", resident, "New note: " + text, "Not urgent. Please come and assess when you can.", staff)
            drafts.pop(rid, None)
            st.session_state.note_flash = f"Note saved. RN {config.RN_NAME} has been told."
            st.rerun()
        if drop.button("Discard", key=f"note_drop_{rid}", use_container_width=True):
            drafts.pop(rid, None)
            st.rerun()


def render_notes(rid):
    notes = store.notes_for(rid)
    if not notes:
        st.write("No notes yet.")
        return
    day = None
    for n in notes:
        if n["day"] != day:
            day = n["day"]
            st.markdown(f"**{day}**")
        extra = "  _(saved in the app)_" if n.get("saved") else ""
        st.markdown(f"- **{n['time']}** {n['staff']}: {n['text']}{extra}")
    st.caption("Fictional demo notes.")


LANGUAGES = ["English", "Malayalam", "Tamil", "Hindi", "Chinese"]
LANG_TAGS = {"English": "en-AU", "Malayalam": "ml-IN", "Tamil": "ta-IN", "Hindi": "hi-IN", "Chinese": "zh-CN"}


def handover_screen(allowed, staff):
    if st.button("Back to all residents"):
        st.session_state.handover_open = False
        st.rerun()
    st.markdown(ui.panel_head("Shift handover", "notes"), unsafe_allow_html=True)
    st.write("What happened on the earlier shifts, for the staff who are starting now. "
             "Notes saved with Voice note appear here by themselves, so nothing needs to be written twice.")
    names = [f"{n} shift" for n, _, _ in handover.SHIFTS]
    default = names[handover.default_incoming(demo_now())]
    if hasattr(st, "segmented_control"):
        pick = st.segmented_control("Handover for the", names, default=default, key="ho_shift") or default
    else:
        pick = st.radio("Handover for the", names, index=names.index(default), horizontal=True, key="ho_shift")
    incoming = names.index(pick)
    st.caption({0: "Morning staff (7am to 3pm) see yesterday afternoon and the night.",
                1: "Afternoon staff (3pm to 11pm) see the morning.",
                2: "Night staff (11pm to 7am) see the morning and the afternoon."}[incoming])

    language = st.selectbox("Short summary in", LANGUAGES)
    store_key = (staff, language)
    results = st.session_state.setdefault("handover_results", {})
    if st.button("Write the handover", type="primary", icon=":material/auto_awesome:", use_container_width=True):
        with st.spinner("Reading the notes..."):
            results[store_key] = handover.generate([r["id"] for r in allowed], language)
    res = results.get(store_key)
    if res and res["error"]:
        st.warning("The short summary could not be written right now, so only the notes and the automatic check are shown. "
                   "Please read the notes or ask the nurse in charge.")
        st.caption("Technical note for the demo builder: " + res["error"])
    spoken = []
    for r in allowed:
        rid = r["id"]
        item = res["items"].get(rid) if res else None
        flagged = res["flags"].get(rid, []) if res else handover.flags(store.notes_for(rid))
        groups = handover.board_events(rid, incoming)
        kinds = sorted({k for g in groups for n in g["notes"] for k in n["kinds"]})
        with st.container(border=True):
            st.markdown(ui.handover_head(r, handover.allergy(rid), kinds), unsafe_allow_html=True)
            if item:
                st.write(item["summary"])
                spoken.append(f"{r['name']}. {item['summary']}")
                if item["tell_rn"]:
                    st.warning("Tell the RN:\n\n" + "\n".join(f"- {t}" for t in item["tell_rn"]))
                if item["watch"]:
                    st.info("Watch:\n\n" + "\n".join(f"- {w}" for w in item["watch"]))
                st.caption("Made from: " + "; ".join(item["sources"]))
            elif res and not res["error"]:
                st.warning("The summary for this resident could not be checked against the notes, so it is not shown. "
                           "Read the notes below.")
            st.markdown(ui.handover_body(handover.care_lines(rid), groups), unsafe_allow_html=True)
            if flagged and res:
                lines = [f"- **{f['kind']}**: " + (f"{f['day']} {f['time']}, {f['staff']}: " if f["time"] else "") + f["text"]
                         for f in flagged]
                with st.expander(f"Automatic check: {len(flagged)} thing(s) in the notes"):
                    st.markdown("\n".join(lines))
    if spoken:
        voice.speak_button(" ".join(spoken), LANG_TAGS.get(language, "en-AU"), label="Read the handover aloud")
    st.caption("Fictional demo data. Always confirm with the care plan or the RN.")


# ---------------------------------------------------------------- task reminders
STATE_CHIP = {"overdue": ("allergy", "Overdue"), "due": ("warn", "Due now"), "soon": ("neutral", "Coming up"),
              "later": ("neutral", "Later"), "missed": ("neutral", "Not ticked"), "done": ("ok", "Done")}


def task_rows(items, staff, prefix, show_resident=True):
    for it in items:
        cls, word = STATE_CHIP[it["state"]]
        when = it["due"] + (f" ({it['label']})" if it["label"] else "")
        head = (f"<b>{html.escape(it['resident'])}</b> · Room {html.escape(str(it['room']))}<br>" if show_resident else "")
        with st.container(border=True, key=f"{prefix}_{it['task_id']}_{it['due'].replace(':', '')}"):
            st.markdown(
                f'<div class="taskrow">{head}{html.escape(it["text"])}</div>'
                f'<div class="chips" style="margin-top:6px"><span class="chip {cls}">{word}: {html.escape(when)}</span>'
                f'<span class="src">{html.escape(it["source"])}</span></div>', unsafe_allow_html=True)
            if it["state"] == "done":
                st.caption(f"Done by {it['done_by']} at {it['done_at']}")
            elif st.button("Done", key=f"{prefix}_done_{it['task_id']}_{it['due'].replace(':', '')}", use_container_width=True,
                           type="primary" if it["state"] in ("due", "overdue") else "secondary"):
                tasks.mark_done(it["resident_id"], it["task_id"], it["due"], staff)
                st.rerun()


def demo_now():
    """The time used for 'due now'. Real time by default; the demo clock lets you show the screen at any hour."""
    if st.session_state.get("real_time", True):
        return datetime.now()
    t = st.session_state.get("demo_clock") or datetime.now().time()
    return datetime.combine(datetime.now().date(), t)


def tasks_screen(allowed, staff):
    if st.button("Back to all residents"):
        st.session_state.tasks_open = False
        st.rerun()
    st.markdown("## Tasks due")
    st.caption("These come straight from each care plan. Tick a task when it is done.")
    with st.expander("Demo clock"):
        st.checkbox("Use the real time", value=True, key="real_time")
        if not st.session_state.get("real_time", True):
            st.time_input("Time now", value=datetime.now().time().replace(second=0, microsecond=0), key="demo_clock", step=900)
    now = demo_now()
    items = tasks.build([r["id"] for r in allowed], now)
    c = tasks.counts(items)
    st.markdown(
        f'<div class="chips"><span class="chip allergy">{c["overdue"]} overdue</span><span class="chip warn">{c["due"]} due now</span>'
        f'<span class="chip neutral">{c["soon"]} coming up</span><span class="chip ok">{c["done"]} done</span></div>'
        f'<div class="foot">Time: {now.strftime("%H:%M")}</div>', unsafe_allow_html=True)
    now_items = [i for i in items if i["state"] in ("overdue", "due")]
    if now_items:
        st.markdown('<div class="sec">Needs doing now</div>', unsafe_allow_html=True)
        task_rows(now_items, staff, "tn")
    else:
        st.success("Nothing is due right now.")
    soon = [i for i in items if i["state"] == "soon"]
    if soon:
        st.markdown('<div class="sec">Coming up in the next 2 hours</div>', unsafe_allow_html=True)
        task_rows(soon, staff, "ts")
    for state, title in (("later", "Later today"), ("missed", "Earlier today, not ticked"), ("done", "Done today")):
        part = [i for i in items if i["state"] == state]
        if part:
            with st.expander(f"{title} ({len(part)})"):
                task_rows(part, staff, "t" + state[0])
    st.caption("Fictional demo data. Always confirm with the care plan or the RN.")


# ---------------------------------------------------------------- training coach
COACH_QUICK = ["How do I use a hoist?", "What do I do if a resident chokes?", "When do I wash my hands?",
               "How do I write an incident report?"]
NO_RESIDENT = {"id": None, "name": "", "room": ""}


def quiz_ui(staff):
    qz = st.session_state.get("quiz")
    if not qz:
        topic = st.selectbox("Topic", ["All topics"] + training.TOPICS)
        n = st.select_slider("How many questions", options=[3, 5, 8], value=5)
        use_ai = st.checkbox("Also make new questions with AI (slower, needs your key)")
        if st.button("Start quiz", type="primary", use_container_width=True):
            qs, source = [], "bank"
            if use_ai:
                try:
                    with st.spinner("Writing new questions from the policies..."):
                        ai = training.ai_questions(topic if topic != "All topics" else "Falls", n)
                    if ai:
                        import random as _r
                        rng = _r.Random()
                        qs, source = [training._shuffled(q, rng) for q in ai], "ai"
                except Exception as err:
                    st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
            if not qs:
                qs = training.pick(topic, n)
            st.session_state.quiz = {"qs": qs, "i": 0, "score": 0, "picked": None, "topic": topic, "source": source, "wrong": [], "saved": False}
            st.rerun()
        hist = store.training_history(staff)
        if hist:
            st.markdown('<div class="sec">Your recent quizzes</div>', unsafe_allow_html=True)
            for h in hist:
                st.markdown(f"- {h['date']}: **{h['topic']}**, {h['score']} out of {h['total']}")
        return

    qs, i = qz["qs"], qz["i"]
    if i >= len(qs):
        if not qz["saved"]:
            store.add_training_result(staff, qz["topic"], qz["score"], len(qs), qz["source"])
            qz["saved"] = True
        with st.container(border=True, key="quiz_result"):
            st.markdown(f"### {qz['score']} out of {len(qs)}")
            st.write(training.grade(qz["score"], len(qs)))
            if qz["wrong"]:
                st.markdown("**To review:**")
                for w in qz["wrong"]:
                    st.markdown(f"- {w['q']}  \n  *{w['options'][w['answer']]}*  \n  {ui.source_row([w['source']])}", unsafe_allow_html=True)
        if st.button("Try another quiz", type="primary", use_container_width=True):
            st.session_state.quiz = None
            st.rerun()
        return

    q = qs[i]
    st.progress(i / len(qs), text=f"Question {i + 1} of {len(qs)}")
    st.markdown(f"### {q['q']}")
    if qz["picked"] is None:
        for idx, opt in enumerate(q["options"]):
            if st.button(opt, key=f"qopt_{i}_{idx}", use_container_width=True):
                qz["picked"] = idx
                if idx == q["answer"]:
                    qz["score"] += 1
                else:
                    qz["wrong"].append(q)
                st.rerun()
        return
    for idx, opt in enumerate(q["options"]):
        mark = "✅" if idx == q["answer"] else ("❌" if idx == qz["picked"] else "▫️")
        st.markdown(f"{mark} {opt}")
    right = qz["picked"] == q["answer"]
    with st.container(border=True, key=f"qfb_{i}"):
        st.markdown(f'<div class="banner {"check" if not right else "urgent"}" style="{"background:#E1F3E8;color:#1F6B3E;border-color:#B7DEC4" if right else ""}">'
                    f'{"Correct" if right else "Not quite"}</div>', unsafe_allow_html=True)
        st.write(q["why"])
        st.markdown(ui.source_row([q["source"]]), unsafe_allow_html=True)
    last = i + 1 >= len(qs)
    if st.button("See my score" if last else "Next question", type="primary", use_container_width=True):
        qz["i"] += 1
        qz["picked"] = None
        st.rerun()


def coach_answer(q):
    heard = None
    if voice.needs_understanding(q) or not voice.looks_english(q):
        try:
            heard = voice.understand_text(q, [])
        except Exception as err:
            st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
    english = (heard or {}).get("english") or None
    try:
        res = rag.answer(q, NO_RESIDENT, mode="coach", english=english, lang_name=(heard or {}).get("language_name") or None,
                         lang_tag=(heard or {}).get("language"), smart=bool(st.session_state.get("smart")))
    except Exception as err:
        st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
        res = {"found": False, "answer": config.could_not_answer((heard or {}).get("language")), "sources": [],
               "language": (heard or {}).get("language") or "en-AU", "english": ""}
    level, _ = rules.classify(english or q)
    if rules.classify(q)[0] == "urgent":
        level = "urgent"
    st.session_state.coach = {"q": q, "res": res, "urgent": level == "urgent"}


def coach_ui():
    q = st.text_input("Ask how to do something", placeholder="How do I use the hoist?", key="coach_text")
    if st.button("Ask", type="primary", use_container_width=True) and q.strip():
        with st.spinner("Looking in the policies..."):
            coach_answer(q.strip())
    with st.container(key="quick"):
        cols = st.columns(2)
        for n, text in enumerate(COACH_QUICK):
            if cols[n % 2].button(text, key=f"coachq_{n}", use_container_width=True):
                with st.spinner("Looking in the policies..."):
                    coach_answer(text)
    got = st.session_state.get("coach")
    if not got:
        st.caption("Answers come only from your facility's policies, with the source. For a resident's own needs, check their care plan.")
        return
    res = got["res"]
    with st.container(border=True, key="coach_card"):
        if got["urgent"]:
            st.markdown('<div class="banner urgent">If this is happening now: press the emergency bell and use the Emergency button on the resident\'s page</div>',
                        unsafe_allow_html=True)
        st.markdown(f"**{html.escape(got['q'])}**")
        st.write(res["answer"])
        if res.get("sources"):
            st.markdown(ui.source_row(res["sources"]), unsafe_allow_html=True)
        if res.get("english"):
            with st.expander("English original (to check the translation)"):
                st.write(res["english"])
        st.markdown(f'<div class="foot">{urgent_i18n.confirm_text(res.get("language"))}</div>', unsafe_allow_html=True)


def learn_screen(staff):
    if st.button("Back to all residents"):
        st.session_state.learn_open = False
        st.session_state.quiz = None
        st.rerun()
    st.markdown("## Training coach")
    st.caption("Quizzes and how-to help, made from your facility's own policies.")
    quiz_tab, ask_tab = st.tabs(["Quiz", "How do I...?"])
    with quiz_tab:
        quiz_ui(staff)
    with ask_tab:
        coach_ui()


def open_record(resident, staff, t):
    """A pop-up to record one chart tile: how much was eaten or drunk, the pain level, or just Done."""
    first = resident["name"].split()[0]

    @st.dialog(f"{t['label']}, {t['due']}")
    def _dialog():
        st.markdown(f"**{resident['name']}**, Room {resident['room']}")
        if t["note"]:
            st.info("Care plan: " + t["note"])
        if t["state"] == "done":
            st.success(f"Done by {t['done_by']} at {t['done_at']}" + (f". {t['value']}." if t["value"] else "."))
            return
        choice = None
        if t["ask"]:
            question = {"meal": f"How much did {first} eat?", "fluid": f"How much did {first} drink?",
                        "pain": f"How is {first}'s pain?"}[t["ask"]]
            if hasattr(st, "segmented_control"):
                choice = st.segmented_control(question, chart.OPTIONS[t["ask"]], key=f"rec_{t['task_id']}_{t['due']}")
            else:
                choice = st.radio(question, chart.OPTIONS[t["ask"]], index=None, key=f"rec_{t['task_id']}_{t['due']}")
        worry = (t["ask"] == "pain" and choice in ("Moderate", "Severe")) or (t["ask"] in ("meal", "fluid") and choice in ("Refused", "A quarter"))
        if worry:
            st.warning("Consider telling the RN about this.")
        need = bool(t["ask"]) and not choice
        if st.button("Save", type="primary", disabled=need, use_container_width=True, key=f"recsave_{t['task_id']}_{t['due']}"):
            tasks.mark_done(resident["id"], t["task_id"], t["due"], staff, value=choice or "")
            st.rerun()
        if worry and st.button("Save and tell the RN", disabled=need, use_container_width=True, key=f"rectell_{t['task_id']}_{t['due']}"):
            tasks.mark_done(resident["id"], t["task_id"], t["due"], staff, value=choice or "")
            new_alert("check", resident, f"{t['label']} at {t['due']}: {choice}.", "Not urgent. Please come and assess when you can.", staff)
            st.rerun()

    _dialog()


def chart_panel(resident, staff):
    rid = resident["id"]
    now = demo_now()
    st.markdown(ui.chart_summary(chart.fluids(rid, now), chart.meals(rid, now)), unsafe_allow_html=True)
    st.caption("Tap a tile to record it. Green means done. Yellow is due now. Red is late.")
    all_tiles = chart.tiles(rid, now)

    def shift_of(t):
        return handover.shift_index(t["due"])
    for idx, (name, hours, _) in enumerate(handover.SHIFTS):
        group = [t for t in all_tiles if shift_of(t) == idx]
        if not group:
            continue
        st.markdown(f'<div class="tilehead">{name} shift ({hours})</div>', unsafe_allow_html=True)
        with st.container(key=f"grid_chart_{rid}_{idx}"):
            for r0 in range(0, len(group), 3):
                cols = st.columns(3)
                for col, t in zip(cols, group[r0:r0 + 3]):
                    key = f"ct_{t['task_id']}_{t['due'].replace(':', '')}"
                    with col, st.container(key=key):
                        st.markdown(ui.chart_tile(t), unsafe_allow_html=True)
                        if st.button(f"{t['label']} {t['due']}", key=f"{key}_b"):
                            open_record(resident, staff, t)


def record_panel(resident, staff):
    rid = resident["id"]
    first = resident["name"].split()[0]
    sel_key = f"rec_sel_{rid}"
    chosen = st.session_state.setdefault(sel_key, [])
    secs = records.sections()
    if st.session_state.get("rec_saved") == rid:
        st.session_state.rec_saved = None
        st.success("Saved. It is in the daily notes and the shift handover.")
    st.caption(f"Tap everything that happened with {first}. You can pick more than one. Then press Save.")
    names = [s["name"] for s in secs]
    pick = st.segmented_control("Section", names, default=names[0], key=f"rec_sec_{rid}", label_visibility="collapsed") or names[0]
    sec = next(s for s in secs if s["name"] == pick)
    with st.container(key=f"grid_rec_{rid}"):
        for r0 in range(0, len(sec["tiles"]), 3):
            cols = st.columns(3)
            for col, t in zip(cols, sec["tiles"][r0:r0 + 3]):
                key = f"ct_rec_{t['id']}"
                with col, st.container(key=key):
                    st.markdown(ui.record_tile(t, t["id"] in chosen), unsafe_allow_html=True)
                    if st.button(t["label"], key=f"{key}_b"):
                        if t["id"] in chosen:
                            chosen.remove(t["id"])
                        else:
                            chosen.append(t["id"])
                        st.rerun()
    if chosen:
        labels = ", ".join(t["label"] for _, t in records.chosen(chosen))
        st.markdown(f'<div class="hoev"><b>Chosen:</b> {labels}</div>', unsafe_allow_html=True)
    note = st.text_area("Anything to add? (optional)", key=f"rec_note_{rid}", height=80)
    lv = records.level(chosen)
    c1, c2 = st.columns(2)
    with c1:
        save = st.button("Save", type="primary", disabled=not chosen, use_container_width=True, key="rec_save")
    with c2:
        clear = st.button("Clear", disabled=not chosen, use_container_width=True, key="rec_clear")
    tell = False
    if lv == "urgent":
        st.error("This looks urgent. Stay with them and press the emergency bell first.")
        tell = st.button("Save and alert the RN now", disabled=not chosen, use_container_width=True, key="rec_tell")
    elif lv == "check":
        tell = st.button("Save and tell the RN", disabled=not chosen, use_container_width=True, key="rec_tell")
    if clear:
        st.session_state[sel_key] = []
        st.rerun()
    if save or tell:
        rec = records.add(resident, staff, list(chosen), note)
        if tell:
            what = records.sentence(chosen, note)
            if lv == "urgent":
                kind = records.urgent_kind(chosen)
                new_alert("urgent", resident, what, "Steps shown to staff:\n" + rules.STEPS[kind]["text"], staff)
            else:
                new_alert("check", resident, what, "Not urgent. Please come and assess when you can.", staff)
        st.session_state[sel_key] = []
        st.session_state.pop(f"rec_note_{rid}", None)
        st.session_state.rec_saved = rid
        st.rerun()


SECTION_ICONS = {"Overview": ":material/person:", "Medical": ":material/medical_services:",
                 "Food and fluids": ":material/restaurant:", "Falls and mobility": ":material/directions_walk:",
                 "Behaviour": ":material/psychology:", "Background": ":material/menu_book:"}


def open_panel(key):
    if key == "ask":
        st.session_state.chat_open = True
    else:
        st.session_state.panel = key
    st.rerun()


def tile_grid(items, key, on_click, per_row=2):
    """A grid of big tiles. items: (id, label, icon, style). Pressing one calls on_click(id)."""
    with st.container(key=key):
        for r in range(0, len(items), per_row):
            cols = st.columns(per_row)
            for col, (k, label, icon, style) in zip(cols, items[r:r + per_row]):
                if col.button(label, icon=icon, key=f"tile_{style}_{key}_{k}", use_container_width=True):
                    on_click(k)


def resident_screen(resident, staff):
    first = resident["name"].split()[0]
    inside = st.session_state.chat_open or st.session_state.get("panel") is not None
    if st.button(f"Back to {first}" if inside else "Back to all residents"):
        if inside:
            st.session_state.chat_open = False
            st.session_state.panel = None
        else:
            st.session_state.sel = None
            st.session_state.show_em = False
        st.rerun()

    rid = resident["id"]
    nflags = len(handover.flags(store.notes_for(rid)))
    st.markdown(ui.resident_head(resident, handover.allergy(rid), nflags), unsafe_allow_html=True)

    @live(5)
    def banner():
        mine = store.alerts_for(resident["id"])
        if mine:
            text, tone = alert_status(mine[-1])
            if mine[-1]["level"] == "urgent" and tone == "warning":
                tone = "error"
            else:
                text = ("Message to RN: " + text) if mine[-1]["level"] != "urgent" else text
            getattr(st, tone)(text)
    banner()

    with st.container(key="em_btn"):
        if st.button("Emergency: alert the RN", use_container_width=True):
            st.session_state.show_em = True
    if st.session_state.show_em:
        with st.container(border=True):
            st.error("Life-threatening? Press the emergency bell and call 000 first. This app does not replace the bell.")
            labels = [e[0] for e in rules.EMERGENCIES]
            choice = st.radio("What is happening?", labels, key="em_choice")
            b1, b2 = st.columns(2)
            with b1.container(key="em_send"):
                send = st.button("Send alert to RN", use_container_width=True)
            if send:
                _, kind, what = next(e for e in rules.EMERGENCIES if e[0] == choice)
                new_alert("urgent", resident, what, "Steps shown to staff:\n" + rules.STEPS[kind]["text"], staff)
                st.session_state.show_em = False
                st.rerun()
            if b2.button("Cancel", use_container_width=True):
                st.session_state.show_em = False
                st.rerun()

    panel = st.session_state.get("panel")
    if not st.session_state.chat_open and panel is None:
        sections = store.resident_sections(resident["id"])
        names = [n for n in sections if n != "Basics"]
        due = chart.attention([rid], demo_now()).get(rid, 0)
        st.markdown('<div class="tilehead">What do you want to do?</div>', unsafe_allow_html=True)
        main = [("record", "Add a record", ":material/add_circle:", "main"),
                ("voice", "Voice note", ":material/mic:", "main"),
                ("ask", f"Ask about {first}", ":material/chat:", "main"),
                ("tasks", f"Care chart ({due} due)" if due else "Care chart", ":material/checklist:", "warn" if due else "main"),
                ("notes", f"Daily notes ({nflags} to check)" if nflags else "Daily notes", ":material/edit_note:",
                 "warn" if nflags else "main")]
        tile_grid(main, "tiles_main", lambda k: open_panel(k))
        st.markdown('<div class="tilehead">Care plan</div>', unsafe_allow_html=True)
        plan = [(n, n, SECTION_ICONS.get(n, ":material/description:"), "plain") for n in names]
        tile_grid(plan, "tiles_plan", lambda k: open_panel(k), per_row=1)
        st.caption("Fictional demo data.")
        return

    if panel is not None and not st.session_state.chat_open:
        sections = store.resident_sections(resident["id"])
        titles = {"voice": "Voice note", "tasks": "Care chart", "notes": "Daily notes", "record": "Add a record"}
        st.markdown(ui.panel_head(titles.get(panel, panel), {"voice": "voice", "tasks": "tasks", "notes": "notes", "record": "notes"}.get(panel, "plan")),
                    unsafe_allow_html=True)
        if panel == "voice":
            st.caption("Press the microphone and speak in any language, or type. I write a clean note for you to check. "
                       "Nothing is saved until you press Save.")
            note_entry(resident, staff, expanded=True)
        elif panel == "record":
            record_panel(resident, staff)
        elif panel == "tasks":
            chart_panel(resident, staff)
        elif panel == "notes":
            render_notes(rid)
        elif panel in sections:
            with st.container(border=True):
                st.markdown(sections[panel])
            st.caption("Fictional demo data.")
        return

    # ---- chat ----
    auto = st.session_state.get("auto_ask")
    if auto and auto[0] == resident["id"]:  # arrived from "open their page and ask there"
        st.session_state.auto_ask = None
        handle_question(auto[1], resident, staff)
    msgs = st.session_state.msgs.setdefault(resident["id"], [])
    if not msgs:
        st.markdown(
            f'<div class="emptychat"><b>Ask about {first}</b><br>Type or speak, in any language. '
            "I answer only from the care plan and policies, and I show the source. "
            "If something sounds serious, I alert the RN for you.<br>"
            '<span style="color:#4A6165;font-size:.9rem">You can say things like “answer in Chinese”.</span></div>',
            unsafe_allow_html=True)
    for i, m in enumerate(msgs):
        render_message(i, m, resident, staff)
    pend = st.session_state.get("pending_tts")
    if pend and pend[0] == resident["id"] and pend[1] < len(msgs):
        st.session_state.pending_tts = None
        m = msgs[pend[1]]
        with st.spinner("Preparing the voice..."):
            try:
                m["audio"] = voice.synthesize(m.get("spoken") or m["text"])
                m["autoplay_audio"] = True
            except Exception as err:  # not available on this key, or busy: use the device voice instead
                st.session_state.last_error = f"voice: {type(err).__name__}: {str(err)[:140]}"
                m["autoplay"] = True
        st.rerun()
    if st.session_state.get("last_error"):
        st.caption("Technical note for the demo builder: " + st.session_state.last_error)

    quick = {
        "Care plan summary": "Give me the care plan summary",
        "Diet and fluids": f"What diet and fluids does {first} need?",
        "Falls": f"Tell me about falls for {first}",
        "What if a fall?": "What do I do if a resident falls?",
    }
    with st.container(key="quick"):
        cols = st.columns(2)
        for n, (label, question) in enumerate(quick.items()):
            if cols[n % 2].button(label, key=f"quick_{n}", use_container_width=True):
                handle_question(question, resident, staff)
                st.rerun()
    if st.button("Not sure? Ask the RN", use_container_width=True):
        ask_rn(resident, staff)
        st.rerun()

    st.toggle("Smarter answers (a little slower)", key="smart",
              help="Uses a stronger AI model. Better for tricky or unusual questions.")
    st.session_state.setdefault("mic_n", 0)
    if st.session_state.get("voice_note"):
        st.warning(st.session_state.pop("voice_note"))
    audio = st.audio_input("Speak your question (any language)", key=f"mic_{st.session_state.mic_n}")
    if audio is not None:
        st.session_state.mic_n += 1  # a fresh, empty recorder after this one
        heard = None
        try:
            with st.spinner("Listening..."):
                heard = voice.transcribe(audio.getvalue(), audio.type or "audio/wav",
                                         names=[r["name"] for r in store.residents_meta()])
        except Exception as err:
            st.session_state.last_error = f"{type(err).__name__}: {str(err)[:160]}"
        if heard and heard["text"]:
            handle_question(heard["text"], resident, staff, voice_q=True, heard=heard)
        else:
            st.session_state.voice_note = "I could not hear a clear question. Please try again, or type it."
        st.rerun()

    q = st.chat_input(f"Ask about {first}...")
    if q:
        handle_question(q, resident, staff)
        st.rerun()


# ---------------------------------------------------------------- main
for key, default in (("sel", None), ("panel", None), ("chat_open", False), ("show_em", False), ("msgs", {})):
    st.session_state.setdefault(key, default)

ui.topbar("For aged care staff")
VIEWS = ["Care staff phone", "RN phone (demo)"]
if hasattr(st, "segmented_control"):
    view = st.segmented_control("View", VIEWS, default=VIEWS[0], label_visibility="collapsed") or VIEWS[0]
else:
    view = st.radio("View", VIEWS, horizontal=True, label_visibility="collapsed")
if view.startswith("RN"):
    rn_view()
    st.stop()

@st.cache_resource(show_spinner="Getting ready (loads the search model once)...")
def warm():
    try:
        rag.warm_up()
        return True
    except Exception as err:  # for example: python ingest.py has not been run yet
        return f"{type(err).__name__}: {str(err)[:160]}"


warm_result = warm()
if warm_result is not True:
    st.warning("The document database is not ready. Run `python ingest.py` in Terminal, then reload this page. "
               f"(Technical note: {warm_result})")

roster = store.roster()
staff = st.selectbox("Signed in as", list(roster), help="Demo roster. Staff only see the residents they are rostered to.")
allowed = [r for r in store.residents_meta() if r["id"] in roster[staff]]  # access control: rostered residents only

if st.session_state.sel not in [r["id"] for r in allowed]:
    st.session_state.sel = None
    st.session_state.chat_open = False

st.session_state.setdefault("handover_open", False)
st.session_state.setdefault("tasks_open", False)
st.session_state.setdefault("learn_open", False)
if st.session_state.sel is None and st.session_state.handover_open:
    handover_screen(allowed, staff)
elif st.session_state.sel is None and st.session_state.tasks_open:
    tasks_screen(allowed, staff)
elif st.session_state.sel is None and st.session_state.learn_open:
    learn_screen(staff)
elif st.session_state.sel is None:
    due = tasks.attention([r["id"] for r in allowed], demo_now())
    hour = datetime.now().hour
    hello = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    total_flags = sum(len(handover.flags(store.notes_for(r["id"]))) for r in allowed)
    summary = [f'<span class="chip neutral">{len(allowed)} residents on your roster</span>']
    if sum(due.values()):
        summary.append(f'<span class="chip warn">{sum(due.values())} tasks due</span>')
    if total_flags:
        summary.append(f'<span class="chip warn">{total_flags} notes to check</span>')
    st.markdown(f'<div class="hello">{hello}, {html.escape(staff.split(",")[0].split()[0])}</div>'
                f'<div class="chips" style="margin:6px 0 14px">{"".join(summary)}</div>', unsafe_allow_html=True)
    with st.container(key="top_actions"):
        if st.button("Shift handover summary", type="primary", icon=":material/swap_horiz:", use_container_width=True):
            st.session_state.handover_open = True
            st.rerun()
        b1, b2 = st.columns(2)
        if b1.button(f"Tasks due ({sum(due.values())})", icon=":material/checklist:", use_container_width=True):
            st.session_state.tasks_open = True
            st.rerun()
        if b2.button("Training coach", icon=":material/school:", use_container_width=True):
            st.session_state.learn_open = True
            st.rerun()
    chart_due = chart.attention([r["id"] for r in allowed], demo_now())
    with st.container(key="grid_residents"):
        for r0 in range(0, len(allowed), 3):
            cols = st.columns(3)
            for col, r in zip(cols, allowed[r0:r0 + 3]):
                with col, st.container(key=f"pt_{r['id']}"):
                    st.markdown(ui.photo_tile(r, handover.allergy(r["id"]), chart_due.get(r["id"], 0)), unsafe_allow_html=True)
                    if st.button(f"Open {r['name'].split()[0]}", key=f"open_{r['id']}"):
                        st.session_state.sel = r["id"]
                        st.rerun()
    st.caption("Tap a photo to open the resident. Red flag: high falls risk. Yellow flag: medium. Blue i: has an allergy. Yellow number: care due now.")
else:
    resident = next(r for r in allowed if r["id"] == st.session_state.sel)
    resident_screen(resident, staff)
