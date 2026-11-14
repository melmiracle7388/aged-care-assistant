"""Compare how fast different Gemini models answer.   python speedtest.py

It asks a tiny question twice per model and prints the seconds. It changes nothing.
"""
import time

from google import genai

client = genai.Client()  # reads GEMINI_API_KEY from your own computer

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
]
PROMPT = "Reply with exactly: OK"

for model in MODELS:
    times = []
    for _ in range(2):
        start = time.perf_counter()
        try:
            client.models.generate_content(model=model, contents=PROMPT).text
            times.append(f"{time.perf_counter() - start:.1f} s")
        except Exception as err:
            times.append(f"failed ({type(err).__name__}: {str(err)[:70]})")
            break
    print(f"{model}: " + " | ".join(times))
