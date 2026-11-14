"""Split the fake resident files and policies into small, labelled sections."""
import json
import re

from config import DATA


def split_sections(text):
    """Return (header_text, [(title, body), ...]) split on lines that start with '## '."""
    parts = re.split(r"^## ", text, flags=re.M)
    sections = []
    for part in parts[1:]:
        title, _, body = part.partition("\n")
        sections.append((title.strip(), body.strip()))
    return parts[0], sections


def _resident_meta():
    items = json.loads((DATA / "residents_meta.json").read_text())
    return {r["id"]: r for r in items}


def load_chunks():
    chunks = []

    meta = _resident_meta()
    for path in sorted((DATA / "residents").glob("R*.md")):
        rid = path.name.split("_")[0]
        info = meta[rid]
        _, sections = split_sections(path.read_text())
        # Allergies are safety-critical, so every section of a resident carries them in its header.
        allergy_match = re.search(r"\*\*Allergies:\*\*\s*(.+)", path.read_text())
        allergies = allergy_match.group(1).strip() if allergy_match else "not recorded"
        for title, body in sections:
            chunks.append({
                "id": f"{rid}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}",
                "text": f"Resident {rid} {info['name']} (Room {info['room']}) | ALLERGIES: {allergies} | {title}\n{body}",
                "meta": {
                    "doc_type": "resident",
                    "resident_id": rid,
                    "source_label": f"{rid} {info['name']}, {title}",
                },
            })

    for path in sorted((DATA / "policies").glob("POL*.md")):
        text = path.read_text()
        m = re.search(r"^# (POL-\d+): (.+)$", text, flags=re.M)
        pol_id, pol_title = m.group(1), m.group(2).strip()
        _, sections = split_sections(text)
        for title, body in sections:
            num = re.match(r"(\d+)\.", title)
            number = num.group(1) if num else "0"
            chunks.append({
                "id": f"{pol_id}-s{number}",
                "text": f"{pol_id} {pol_title} | Section {title}\n{body}",
                "meta": {
                    "doc_type": "policy",
                    "resident_id": "",
                    "source_label": f"{pol_id} {pol_title}, section {number}",
                },
            })
    return chunks
