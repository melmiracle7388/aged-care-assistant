# CareAsk demo (fictional data only)

A chatbot for aged care staff. It answers only from the facility documents, shows the source, and alerts an RN when something sounds serious.

**Everything here is fake.** Never put real resident information into this demo or any public AI tool.

## Set up (Mac, one time)

Open Terminal, then:

1. Go into this folder. Type `cd ` (with a space), drag the folder into the Terminal window, press Enter.
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`   (you should see `(.venv)` at the start of the line)
4. `pip install -r requirements.txt`
5. `python tests.py`   (should end with "All checks passed.")

## Add your API key (in YOUR Terminal only)

Gemini (free key from aistudio.google.com/apikey):

`export GEMINI_API_KEY="paste-your-key-here"`

Do this in the same Terminal window each time you start. Do not put the key in any file you share.

The app uses the fast Gemini model `gemini-3.5-flash-lite` by default. For more careful answers, use the bigger model: `export CARE_MODEL="gemini-3.8-flash"`. Go back to the default with `unset CARE_MODEL`.

Prefer Anthropic instead? `export ANTHROPIC_API_KEY="..."` and `export CARE_PROVIDER=anthropic`.

Each answer in the app shows how many seconds the search and the AI took, so you can compare models on your 20 test questions.

The free tier has usage limits. If you see a quota or rate-limit message under the chat, wait a minute and try again.

## Build the database (step 2)

`python ingest.py`   (first run downloads a small model, about 80 MB, so it needs internet)

It should print: `Stored 104 sections in Chroma (70 resident, 34 policy).`

## Test from the Terminal (no screen)

`python cli.py R001 "What diet does she need?"`
`python cli.py R001 "What do I do if a resident falls?"`
`python cli.py R009 "What language does she speak?"`

## Run the app

`streamlit run app.py`

It opens in your browser. Open a second browser tab on the same address and pick "RN phone (demo)" to see alerts arrive.

## Files

- `data/` the fake residents and policies (change them, then run `python ingest.py` again)
- `chunker.py` splits documents into sections
- `ingest.py` stores the sections in Chroma
- `rag.py` finds the right sections and asks the AI (Gemini or Claude) to answer only from them
- `rules.py` fixed red-flag rules (urgent / check / info). The AI can only raise the level, never lower it
- `store.py` alerts and the search log (`logs/search_log.jsonl`)
- `app.py`, `ui.py` the screen

## Safety built in

- Answers come only from the documents, with the source shown and a "confirm with the care plan or RN" note
- "Not found, check with the nurse in charge" when unsure
- Staff only see the residents on their roster (demo roster in `data/roster.json`)
- Every question is saved in the search log
- The app never replaces the emergency bell or calling 000

## Not built yet

Voice input and spoken answers, a real nurse-call connection (needs the facility's IT team), and real login.

## Voice and languages

- In the chat, press the microphone ("Speak your question"), talk, and press stop. Gemini turns your speech into text (any language) and the app answers.
- Ask for another language by saying it: "What diet does she need? Answer in Chinese." The English original is always shown under a translated answer, so staff can check it.
- Press "Speak the answer" under any answer to hear it. The voice comes from your own device, so a language works only if your device has a voice for it (Mac: System Settings > Accessibility > Spoken Content > System Voice).
- Use Chrome and allow the microphone when asked.
- Talk mode: when you ASK by voice, the answer is also read out loud automatically, as a short, plain version (the full answer and the source stay on screen).
- Understanding: the app always shows the AI every section of the selected resident, so messy grammar, short phrases or another language do not make it miss the answer. When you speak, it also works out the plain-English meaning and the language, and answers in the language you used. If it cannot tell what you mean, it asks you one short question instead of just saying "ask the RN".
- Busy Google: if the AI service says "high demand" (503), the app retries and then tries a backup model (`CARE_FALLBACK_MODEL`, default gemini-3.8-flash). A wrong key is not retried.
- Friendly voice: for spoken questions, Google's text-to-speech (`gemini-3.8-flash-lite-tts`, voice Sulafat) reads the short answer. Change the voice with `export CARE_VOICE=Achird` (also Kore, Vindemiatrix), or use the device voice with `export CARE_TTS=browser`. If Google's voice is not available on your key, the app uses the device voice by itself.

## Shift handover and daily notes

- Each resident has fictional "Daily notes" (3 days) in `data/notes/`. See them in the "Daily notes" tab of a resident.
- On the resident list, press "Shift handover summary", choose a language, press "Write the handover". The AI writes a short summary per resident, only from the notes, and names the notes it used. A summary with no source note is not shown.
- An "Automatic check" (fixed rules, not AI) always lists risky wording in the notes: falls, eating less (and a 3-day trend), coughing, pain, skin redness, dizziness, confusion. The AI cannot hide these.
- If Google is busy, the automatic check still works.

## Voice to documentation

- Open a resident, then the "Daily notes" tab, then "Add a note: speak or type". Speak in any language (or type). The app drafts a clean English care note from ONLY what you said.
- You always check and can edit the note first. Nothing is saved until you press "Save note". The original words you spoke are kept with the note.
- If the note mentions something risky (a fall, pain, eating less, coughing...), a warning shows and "Save and tell the RN" saves the note and sends the RN a message. Urgent wording tells you to use the Emergency button.
- Saved notes appear in "Daily notes" and are included in the next shift handover. They are stored in `logs/notes.jsonl` on your computer (fictional demo only).

## Urgent steps in your language
When something sounds urgent (a fall, choking...), the steps are fixed text, not AI. They are written in Malayalam, Tamil, Hindi and Chinese (`urgent_i18n.py`) and the English version is kept under "English original". Please have a native speaker check the wording before any real use.
The same goes for the "tell the RN" note and "Always confirm with the care plan or the RN."

## Design
Font: Atkinson Hyperlegible Next (made for easy reading, bundled in `static/fonts`). Theme and options are in `.streamlit/config.toml` (static files must be switched on there). Run `streamlit run app.py` from the project folder so these files are found.
Red is used only for emergencies, amber for "check", teal for normal actions.

## When the answer is not in the documents
The app shows the topics it does have for that resident (diet, falls, medical...) and an "Ask the RN about this" button that sends the RN a message.

## Smarter answers
- Yes/no questions ("is he blind?", "does she use glasses?"): if the care plan does not list it, the answer is "No. According to the care plan he is not blind", with a "Not listed in the care plan" tag and the sections checked. If it is listed, the answer is "Yes" with the details.
- Answers always come back in the language you used, in its own script. If the AI slips into English, the app asks again once.
- The chat remembers the last few questions, so "what about his diet?" works.
- After an answer, up to 3 follow-up questions are offered as buttons.

## "What do I do if he falls?" (conditional wording)
If the wording is conditional ("if", "in case") but the AI thinks it may be an emergency, the app first asks "Is something happening right now?" with two buttons. Yes alerts the RN at once. No gives the general answer. Clear emergencies ("he fell", "she is choking") still alert straight away.
Allergies are only mentioned in answers about food, drink, medicines or a full summary.

## Smarter answers switch and Claude
In the chat there is a "Smarter answers (a little slower)" switch. It uses a stronger model (default gemini-3.8-flash; change with `export CARE_SMART_MODEL="name"`).
For Claude-level answers, run with `export CARE_PROVIDER=anthropic` and `export ANTHROPIC_API_KEY=...` (needs an Anthropic API account with credits). The app already supports it.

## Task reminders (button: "Tasks due")
Care tasks come straight from each care plan (`data/care_tasks.json`; each task names the care plan section it came from). No AI, so a reminder is never invented. The screen shows Needs doing now, Coming up, Later, Earlier not ticked and Done. Press Done to tick a task; it is saved with the name and time (`logs/tasks_done.jsonl`).
Meal times are set in `tasks.py` (breakfast 08:00, lunch 12:30, tea 17:00). The "Demo clock" box lets you show the screen at any hour. Each resident also has a Tasks tab, and the resident list shows "N tasks due".

## Training coach (button: "Training coach")
- Quiz: 18 hand-written questions from the 6 policies (`data/training_bank.json`). Pick a topic and a length, get instant feedback with the policy source, and a score at the end (saved in `logs/training.jsonl`). Tick "make new questions with AI" for extra questions; each is checked before it is shown.
- How do I...?: ask in any language; the answer comes only from the policies, with the source. If you type an emergency it shows a warning to use the emergency bell.

## Tile design
Opening a resident shows big tiles: Voice note, Ask, Tasks, Daily notes, then one tile per care plan section (Overview, Medical, Food and fluids, Falls and mobility, Behaviour, Background). Press a tile to open it; "Back to <name>" returns to the tiles. The Voice note tile opens ready to speak or type.

## Premium design pass
Spruce hero panel for each resident, action tiles with icon discs, care plan rows with a chevron, a greeting and summary on the residents list, and softer shadows and corners that step down by importance. Red is used only for emergencies, amber only for "needs attention".

## Safer, smarter chat
- A question that names a different resident ("What does Colin eat?" on Frank's page) is never answered with the open resident's data. The app says whose page is open and offers a button to open the other page and ask there (only for residents on the roster).
- "Can he fall? What can I do?" is a risk question, not an emergency. If the AI still marks it urgent, the app asks "Is something happening right now?" before alerting the RN.
- The language comes from the script when the AI is busy, so Malayalam, Tamil, Hindi and Chinese questions are answered in their own language.

## Allergy remarks only when they matter
The allergy lines are removed from what the AI sees unless the question is about food, drink, medicine, allergies or a general summary. So "family details" or "what do I do after a fall" can no longer end with a fish allergy note.

## Shift handover board
The handover screen shows every rostered resident with photo, room, food and help from the care plan, then what happened on the earlier shifts. Shifts: Morning 7am to 3pm, Afternoon 3pm to 11pm, Night 11pm to 7am. Afternoon staff see the morning; night staff see the morning and the afternoon; morning staff see yesterday afternoon and the night. Notes saved with Voice note (hygiene, meals, falls, a lost hearing aid) appear by themselves. The board uses no AI; "Write the handover" adds an optional short summary in simple words, in any supported language.

## Photo grid and care chart

- **Residents list** is a photo grid (3 per row): photo, first name and initial, room, small badges (red/yellow flag = falls risk, blue i = allergy, number = care due now). Tap a photo to open the resident.
- **Care chart** (resident page > Care chart): a tile for each care item of the day (meals, drinks, toilet, wash, mouth care, repositioning, pain and night checks). White = not yet due, yellow = due now, red = late, green with a tick = done and the time it was done.
- Tap a tile to record it (for example "ate half", "drank 200 ml", "mild pain"). Worrying answers have a "Save and tell the RN" button.
- Top tiles show drinks so far against the day's target and meals recorded.
- Everything recorded appears in the **Shift handover** for the next shift. No AI is used on the chart, so it cannot invent anything.
- The routine is in `data/chart_routine.json`; each resident's own tasks come from `data/care_tasks.json`. All names and data are fictional.

## Picture records ("Add a record")

- Resident page > **Add a record**: 9 sections (Food and fluids, Toileting, Mobility, Personal care, Medical, Feelings, Sleep, Activities, Communication) with about 80 picture tiles (`data/record_tiles.json`).
- Tap one or many tiles, across sections, add an optional note, press Save. Tiles marked "check" offer **Save and tell the RN**. Fall, Choking and Hospital offer **Save and alert the RN now** and show the emergency steps.
- Each save writes a structured record (`logs/records.jsonl`, for the nurse review screen and the ML models later) and a plain-language note, so it appears in Daily notes and the Shift handover.
- No AI is used to save a record. All data is fictional.
