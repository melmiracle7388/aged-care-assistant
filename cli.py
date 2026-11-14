"""Quick test from the Terminal, no screen needed.

Example:  python cli.py R001 "What diet does she need?"
"""
import json
import sys

import rag
import rules
import store

if len(sys.argv) < 3:
    sys.exit('Usage: python cli.py R001 "your question"')

rid = sys.argv[1]
question = " ".join(sys.argv[2:])
resident = next((r for r in store.residents_meta() if r["id"] == rid), None)
if resident is None:
    sys.exit(f"No resident {rid}. Try R001 to R010.")

import config

level, kind = rules.classify(question)
print(f"AI service: {config.provider()} ({config.model_name()})")
print(f"Rule check: {level} ({kind})")
print("(Loading the search model on first use can take a while; the app loads it once and stays fast.)")
print(json.dumps(rag.answer(question, resident), indent=2, ensure_ascii=False))
