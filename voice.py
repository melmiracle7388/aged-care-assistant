"""Voice: speech to text (Gemini listens, any language) and text to speech (the device's own voices, free)."""
import json
import re

import streamlit as st
import streamlit.components.v1 as components

import config
import retry

LANG_NAMES = {"en": "English", "ml": "Malayalam", "ta": "Tamil", "hi": "Hindi", "zh": "Chinese", "yue": "Cantonese",
              "ar": "Arabic", "el": "Greek", "it": "Italian", "vi": "Vietnamese", "pa": "Punjabi", "ne": "Nepali",
              "es": "Spanish", "fr": "French", "de": "German", "ja": "Japanese", "ko": "Korean", "tl": "Filipino",
              "id": "Indonesian", "bn": "Bengali", "te": "Telugu", "kn": "Kannada", "ur": "Urdu", "pl": "Polish"}

TRANSCRIBE_PROMPT = """A care worker in an Australian aged care home is asking a voice assistant a question about a resident.
They may have an accent, make grammar mistakes, speak in short phrases, or speak any language (English, Malayalam, Tamil, Hindi, Chinese and others).
Words you may hear: IDDSI, pureed, minced and moist, thickened fluids, falls risk, care plan, allergy, RN, PCW, walking frame, hoist, pressure injury, Wattle Wing, Banksia Wing, Jacaranda Wing.
Resident names you may hear: {names}.

Reply with ONLY one JSON object:
{{"original": "exactly what they said, in the language and script they spoke (do not translate)",
  "english": "what they mean, as one clear plain English sentence with grammar fixed",
  "language": "language tag such as en-AU, ml-IN, ta-IN, hi-IN, zh-CN",
  "language_name": "English name of the language, such as English or Malayalam"}}
If there is no clear speech, reply with exactly: {{"original": ""}}"""

TEXT_PROMPT = """A care worker in an Australian aged care home typed this question to an assistant about a resident.
It may be in any language and may have grammar or spelling mistakes.
Resident names you may see: {names}.

QUESTION: {text}

Reply with ONLY one JSON object:
{{"original": "the question exactly as typed",
  "english": "what they mean, as one clear plain English sentence with grammar fixed",
  "language": "language tag such as en-AU, ml-IN, ta-IN, hi-IN, zh-CN",
  "language_name": "English name of the language, such as English or Malayalam"}}"""

_client = None


def clean_lang(tag, default="en-AU"):
    """Only accept a plain language tag such as en-AU, ml-IN or zh-CN."""
    tag = (tag or "").strip()
    return tag if re.fullmatch(r"[a-z]{2,3}(-[A-Za-z0-9]{2,8})*", tag) else default


def _heard(raw):
    """Turn the model's JSON reply into a dict with text, english, language, language_name (all safe strings)."""
    match = re.search(r"\{.*\}", raw or "", flags=re.S)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    text = str(data.get("original") or "").strip()
    if not text or "[unclear]" in text.lower():
        return {"text": "", "english": "", "language": "en-AU", "language_name": ""}
    lang = clean_lang(data.get("language"))
    name = str(data.get("language_name") or "").strip()[:30]
    name = re.sub(r"[^A-Za-z ()-]", "", name) or LANG_NAMES.get(lang.split("-")[0], "")
    return {"text": text, "english": str(data.get("english") or "").strip(), "language": lang, "language_name": name}


def _model():
    return config.model_name() if config.provider() == "gemini" else config.DEFAULT_MODELS["gemini"]


def _gemini():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()  # reads GEMINI_API_KEY from your own computer
    return _client


def transcribe(audio_bytes, mime="audio/wav", names=()):
    """Listen to the audio. Returns {"text", "english", "language", "language_name"}; text is "" if nothing clear."""
    from google.genai import types
    prompt = TRANSCRIBE_PROMPT.format(names=", ".join(names) or "none")
    contents = [prompt, types.Part.from_bytes(data=audio_bytes, mime_type=mime)]
    reply = retry.call_with_retry(lambda: _gemini().models.generate_content(model=_model(), contents=contents))
    return _heard(reply.text)


def understand_text(text, names=()):
    """Same as transcribe, for a typed question (used when it is not plain English letters)."""
    prompt = TEXT_PROMPT.format(names=", ".join(names) or "none", text=text)
    reply = retry.call_with_retry(lambda: _gemini().models.generate_content(model=_model(), contents=prompt))
    return _heard(reply.text)


def _wav(pcm, rate=24000):
    """Wrap raw 16-bit mono audio in a WAV header so the browser can play it."""
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def synthesize(text):
    """Turn text into a warm, friendly spoken WAV with Google's text-to-speech. Raises an error if it cannot."""
    from google.genai import types
    text = speakable(text)[:1000]
    if hasattr(types, "SpeechMetadata"):
        part = types.Part(text=text, speech_metadata=types.SpeechMetadata(style=config.TTS_STYLE))
    else:
        part = types.Part(text=f"Say this in a {config.TTS_STYLE} voice: {text}")
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.tts_voice()))),
    )
    reply = retry.call_with_retry(lambda: _gemini().models.generate_content(
        model=config.TTS_MODEL, contents=[types.Content(role="user", parts=[part])], config=cfg), tries=2)
    blob = reply.candidates[0].content.parts[0].inline_data
    data = blob.data
    return data if data[:4] == b"RIFF" else _wav(data)


def play(wav_bytes, autoplay=False):
    """Show a small audio player for the friendly voice. It starts by itself when autoplay is True."""
    try:
        st.audio(wav_bytes, format="audio/wav", autoplay=autoplay)
    except TypeError:  # older Streamlit without autoplay
        st.audio(wav_bytes, format="audio/wav")


def needs_understanding(text):
    """True when the text has letters outside plain English (Malayalam, Chinese, Hindi, accents...)."""
    return any(ch.isalpha() and ord(ch) > 127 for ch in text or "")


COMMON_ENGLISH = set("""a an the is are was were be do does did can could should would will what which who how when where why
 i you he she they we it me him her his their my your our this that these those of to in on at for with about from and or not no yes
 please tell show give need needs want has have had if now ok okay help diet food eat eating drink fluids fluid fall falls fell walk
 walker mobility care plan allergy allergies risk meal meals medicine medication pain bed room bell staff nurse rn summary""".split())


def looks_english(text):
    """Rough check: does a typed question contain ordinary English words? Romanised Malayalam or Hindi does not."""
    words = re.findall(r"[a-z']+", (text or "").lower())
    return not words or any(w in COMMON_ENGLISH for w in words)


def speakable(text):
    """Remove markdown marks so the voice does not read symbols out loud."""
    return re.sub(r"[*#_`>]", "", text or "").strip()


def speak_button(text, lang="en-AU", label="Speak the answer", auto=False):
    """A button that reads the text aloud using the device's own voices."""
    payload = json.dumps({"t": speakable(text), "l": clean_lang(lang), "label": label, "auto": bool(auto)}).replace("</", "<\\/").replace("<!--", "<\\!--")
    html = (
        """
<button id="b" style="width:100%;min-height:46px;font-size:18px;font-weight:700;border-radius:14px;
  border:1.5px solid #9FD0CE;background:#E3F1F0;color:#0A5F5E;cursor:pointer;font-family:system-ui,-apple-system,sans-serif"></button>
<script>
const p = __PAYLOAD__;
const b = document.getElementById('b');
// Speak through the main page: it has already been clicked (the microphone), so Chrome allows it,
// and the voice keeps going even when this little box is redrawn.
let W = window;
try { if (window.parent && window.parent.speechSynthesis) { W = window.parent; } } catch (e) {}
const s = W.speechSynthesis;
b.textContent = p.label;
b.onclick = () => {
  if (!s) { b.textContent = 'This device cannot speak'; return; }
  if (s.speaking && !p.auto) { s.cancel(); b.textContent = p.label; return; }
  s.cancel();
  const u = new W.SpeechSynthesisUtterance(p.t);
  u.lang = p.l; u.rate = 1.0; u.pitch = 1.05;
  // pick the most natural voice this device has for the language
  const want = p.l.split('-')[0].toLowerCase();
  const score = (v) => {
    const n = v.name.toLowerCase();
    let sc = 0;
    if (v.lang.toLowerCase().replace('_', '-') === p.l.toLowerCase()) sc += 2;
    if (/premium|enhanced|natural|neural|siri/.test(n)) sc += 4;
    if (n.includes('google')) sc += 2;
    if (/compact|novelty|whisper|bad|bells|boing|zarvox|trinoids/.test(n)) sc -= 5;
    return sc;
  };
  try {
    const all = s.getVoices ? s.getVoices() : [];
    const pool = all.filter(v => v.lang.toLowerCase().replace('_', '-').split('-')[0] === want);
    if (pool.length) { pool.sort((a, b) => score(b) - score(a)); u.voice = pool[0]; }
  } catch (e) { /* keep the default voice */ }
  u.onend = () => { b.textContent = p.label; };
  u.onerror = () => { b.textContent = p.label; };
  b.textContent = 'Stop';
  s.speak(u);
};
// Talk mode: read a spoken question's answer out loud straight away (the browser allows it after you used the microphone)
if (p.auto && s) { b.click(); }
</script>
""".replace("__PAYLOAD__", payload)
    ).strip()
    if hasattr(st, "iframe"):  # newer Streamlit; components.html is being retired
        st.iframe(html, height=58)
    else:
        components.html(html, height=58)
