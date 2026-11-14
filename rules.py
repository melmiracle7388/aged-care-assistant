"""Fixed red-flag rules. These run BEFORE the AI and do not depend on it.

The AI may only raise the level (never lower it). See rag.py.
"""
import re

LEVELS = {"none": 0, "check": 1, "urgent": 2}

# A question about a rule or "what if" is NOT an emergency. "What do I do?" alone is ambiguous: it only stays
# calm when nothing has actually happened (past event words below).
HYPOTHETICAL = re.compile(r"(what if|if a resident|if someone|if anyone|if a client|procedure|policy|in case of)")
WEAK_HYPOTHETICAL = re.compile(r"(what do i do|what should i do|how do i|how should i)")
HAPPENED = re.compile(
    r"(\bfell\b|fallen|on the floor|found (her|him|them)|"
    r"(she|he|they|resident) (is|are|was|has|have|had) (just )?(choking|not breathing|bleeding|collapsed|unresponsive|having a seizure)|"
    r"just collapsed|stopped breathing)"
)
URGENT = re.compile(
    r"(not breathing|stopped breathing|unresponsive|unconscious|chok|can't breathe|cannot breathe|"
    r"chest pain|collapsed|seizure|bleeding|blue lips|\bfell\b|fallen|on the floor|"
    r"hit (his|her|their) head|head strike|broken|fracture)"
)
CHECK = re.compile(
    r"(refus|not eating|not drinking|vomit|diarrh|fever|cough|confus|drowsy|sleepy|rash|swelling|"
    r"bruise|skin tear|agitat|dizzy|unwell|not well|pain|sore)"
)

STEPS = {
    "fall": {
        "text": "1. Stay with them. Press the emergency bell.\n2. Do not move them if you suspect an injury.\n"
                "3. Keep them warm and calm.\n4. The RN assesses before they are moved.\n"
                "5. Complete an incident report before the end of your shift.",
        "source": "POL-001 Falls Prevention and Response, section 4; POL-004",
    },
    "choke": {
        "text": "1. Stay with them. Press the emergency bell.\n2. If they can cough, encourage them to keep coughing.\n"
                "3. If they cannot cough, speak or breathe, use your first aid training.\n"
                "4. The RN or a colleague calls 000.",
        "source": "POL-005 Texture-Modified Diets and Choking, section 5",
    },
    "breath": {
        "text": "1. Stay with them. Press the emergency bell.\n2. Check if they respond and are breathing.\n"
                "3. If they are not breathing, the RN or a colleague calls 000.",
        "source": "POL-006 Reporting Changes in a Resident's Condition, section 5",
    },
    "chest": {
        "text": "1. Stay with them. Keep them still and calm.\n2. Press the emergency bell.\n"
                "3. Do not give food, drink or medicine.",
        "source": "POL-006 Reporting Changes in a Resident's Condition, section 5",
    },
    "bleed": {
        "text": "1. Press firmly on the wound with a clean pad.\n2. Press the emergency bell.\n"
                "3. Stay with them until the RN arrives.",
        "source": "POL-006 Reporting Changes in a Resident's Condition, section 5",
    },
    "other": {
        "text": "1. Stay with them.\n2. Press the emergency bell.\n3. Tell the RN what you can see.",
        "source": "POL-006 Reporting Changes in a Resident's Condition, section 5",
    },
}

EMERGENCIES = [
    ("Fall", "fall", "Resident has fallen"),
    ("Choking", "choke", "Resident is choking"),
    ("Not breathing or not responding", "breath", "Resident is not breathing or not responding"),
    ("Chest pain or severe pain", "chest", "Chest pain or severe pain"),
    ("Bleeding or injury", "bleed", "Bleeding or injury"),
    ("Something else serious", "other", "Other serious concern"),
]


def classify(text):
    """Return (level, type). level is 'none', 'check' or 'urgent'."""
    t = text.lower()
    if HYPOTHETICAL.search(t):
        return "none", "none"
    if WEAK_HYPOTHETICAL.search(t) and not HAPPENED.search(t):
        return "none", "none"
    if URGENT.search(t):
        if re.search(r"(\bfell\b|fallen|floor|head)", t):
            return "urgent", "fall"
        if "chok" in t:
            return "urgent", "choke"
        if re.search(r"(breath|unresponsive|unconscious|collapsed|seizure|blue)", t):
            return "urgent", "breath"
        if "chest" in t:
            return "urgent", "chest"
        if re.search(r"(bleed|broken|fracture)", t):
            return "urgent", "bleed"
        return "urgent", "other"
    if CHECK.search(t):
        return "check", "none"
    return "none", "none"


def higher(a, b):
    """Return the more serious of two levels."""
    return a if LEVELS[a] >= LEVELS[b] else b
