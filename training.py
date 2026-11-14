"""Training coach: policy quizzes and "how do I...?" help. Everything comes from the facility's own policies.

The question bank (data/training_bank.json) is written by hand from the policies and checked, so the quiz works
without any AI. AI-made questions are optional, and every one is checked before it is shown.
"""
import json
import random
import re

import rag
from config import DATA

TOPICS = ["Falls", "Safe transfers", "Infection control", "Incident reports", "Diets and choking", "Reporting changes"]


def load_bank():
    return json.loads((DATA / "training_bank.json").read_text())


def _shuffled(q, rng):
    """A copy of the question with the options in a random order (so the right answer is not always second)."""
    order = list(range(len(q["options"])))
    rng.shuffle(order)
    return {**q, "options": [q["options"][i] for i in order], "answer": order.index(q["answer"])}


def pick(topic, n, rng=None, pool=None):
    """n questions for a topic ('All topics' for a mix), options shuffled."""
    rng = rng or random.Random()
    pool = pool if pool is not None else load_bank()
    items = [q for q in pool if topic in (None, "All topics") or q["topic"] == topic]
    rng.shuffle(items)
    return [_shuffled(q, rng) for q in items[:n]]


# ---------- optional: new questions made by the AI, always checked ----------
AI_PROMPT = """You write training quiz questions for aged care workers, ONLY from the policy text below.
Write {n} multiple-choice questions. Each has 4 options and exactly one correct option. Use plain words.
Every question must be answerable from the policy text. Never use outside knowledge. No questions about medicines or doses.

POLICY TEXT:
{context}

Reply with ONLY a JSON list. Each item:
{{"q": "...", "options": ["...", "...", "...", "..."], "answer": 0, "why": "one sentence from the policy", "source": "S1"}}
"answer" is the index (0 to 3) of the correct option and "source" is the id of the policy section you used."""


def validate_ai(items, sections, topic):
    """Keep only well-formed questions whose source is one of the sections we gave. Returns shuffled-ready dicts."""
    labels = {f"S{i}": s["label"] for i, s in enumerate(sections, 1)}
    good = []
    for it in items or []:
        try:
            q = str(it["q"]).strip()
            opts = [str(o).strip() for o in it["options"]]
            ans = int(it["answer"])
            why = str(it["why"]).strip()
            src = labels.get(str(it["source"]).strip())
        except (KeyError, TypeError, ValueError):
            continue
        if not q or not why or not src or len(opts) != 4 or len(set(opts)) != 4 or not all(opts) or not 0 <= ans <= 3:
            continue
        good.append({"id": f"AI{len(good) + 1}", "topic": topic, "q": q, "options": opts, "answer": ans, "why": why, "source": src})
    return good


def ai_questions(topic, n=5, llm=None, col=None):
    """Ask the AI for new questions about a topic. Returns validated questions (maybe fewer than n, maybe none)."""
    col = col or rag.collection()
    res = col.get(where={"doc_type": "policy"})
    sections = [{"label": m["source_label"], "text": d} for d, m in zip(res["documents"], res["metadatas"])]
    sections.sort(key=lambda s: s["label"])
    key = {"Falls": "POL-001", "Safe transfers": "POL-002", "Infection control": "POL-003", "Incident reports": "POL-004",
           "Diets and choking": "POL-005", "Reporting changes": "POL-006"}.get(topic)
    if key:
        sections = [s for s in sections if s["label"].startswith(key)]
    context = "\n\n".join(f"[S{i}] {s['label']}\n{s['text']}" for i, s in enumerate(sections, 1))
    raw = (llm or (lambda p: rag.ask_model("You write quiz questions.", p)))(AI_PROMPT.format(n=n, context=context))
    m = re.search(r"\[.*\]", raw or "", flags=re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        items = []
    return validate_ai(items, sections, topic)[:n]


def grade(score, total):
    if total == 0:
        return ""
    pct = score / total
    if pct == 1:
        return "Perfect score. Well done."
    if pct >= 0.8:
        return "Great work."
    if pct >= 0.6:
        return "Good. Read the explanations for the ones you missed."
    return "Worth another go. Read the explanations, then try again."
