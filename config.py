"""Shared settings for the CareAsk demo (fictional data only)."""
import os
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
DB_PATH = BASE / "chroma_db"
LOG_DIR = BASE / "logs"
COLLECTION = "carehome"

RN_NAME = "Sarah Collins"
NOT_FOUND = "Not found in the documents. Please check with the nurse in charge."
NOT_FOUND_LOCAL = {
    "ml": "ഡോക്യുമെന്റുകളിൽ കണ്ടെത്താനായില്ല. ദയവായി ചുമതലയുള്ള നഴ്സിനോട് ചോദിക്കുക.",
    "ta": "ஆவணங்களில் கிடைக்கவில்லை. தயவுசெய்து பொறுப்பு செவிலியரிடம் கேளுங்கள்.",
    "hi": "दस्तावेज़ों में नहीं मिला। कृपया इंचार्ज नर्स से पूछें।",
    "zh": "文件中未找到。请向当班护士询问。",
}


def not_found_text(lang_tag):
    return NOT_FOUND_LOCAL.get((lang_tag or "en").split("-")[0], NOT_FOUND)

# gemini-3.5-flash-lite is the fastest. For more careful answers: export CARE_MODEL="gemini-3.8-flash"
DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "anthropic": "claude-sonnet-5-5"}


def provider():
    """Which AI service to use. Set CARE_PROVIDER=gemini or anthropic to force one.

    Otherwise: Gemini if GEMINI_API_KEY is set, Anthropic if ANTHROPIC_API_KEY is set, else Gemini.
    """
    forced = os.environ.get("CARE_PROVIDER", "").lower()
    if forced in DEFAULT_MODELS:
        return forced
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "gemini"


def model_name():
    """Change the model with:  export CARE_MODEL="name-of-model"  before running."""
    return os.environ.get("CARE_MODEL") or DEFAULT_MODELS[provider()]


def smart_model():
    """Used when 'Smarter answers' is switched on (slower, better reasoning). Change with: export CARE_SMART_MODEL="name" """
    if provider() == "anthropic":
        return os.environ.get("CARE_SMART_MODEL") or model_name()
    return os.environ.get("CARE_SMART_MODEL", "gemini-3.8-flash")


def fallback_model():
    """Tried once if the main model stays busy. Change with: export CARE_FALLBACK_MODEL="name" """
    return os.environ.get("CARE_FALLBACK_MODEL", "gemini-3.8-flash")


# Spoken by Google's text-to-speech. Warm voices: Sulafat (warm), Achird (friendly), Kore, Vindemiatrix (gentle).
# export CARE_VOICE=Achird to change it, export CARE_TTS=browser to use the device's own voice (instant, less pleasant).
TTS_MODEL = os.environ.get("CARE_TTS_MODEL", "gemini-3.8-flash-lite-tts")
TTS_STYLE = "warm, friendly and calm, like a kind colleague talking to a friend, at a natural pace"


def tts_voice():
    return os.environ.get("CARE_VOICE", "Sulafat")


def google_tts_on():
    return os.environ.get("CARE_TTS", "google").lower() != "browser" and provider() == "gemini"


# Shown when the AI service cannot answer. Keyed by the first part of the language tag.
COULD_NOT_ANSWER = {
    "en": "The assistant could not answer right now. Please check with the nurse in charge.",
    "ml": "ഇപ്പോൾ ഉത്തരം നൽകാൻ കഴിഞ്ഞില്ല. ദയവായി ചുമതലയുള്ള നഴ്സിനോട് ചോദിക്കുക.",
    "ta": "இப்போது பதில் அளிக்க முடியவில்லை. பொறுப்பிலுள்ள செவிலியரிடம் கேளுங்கள்.",
    "hi": "अभी जवाब नहीं दे सका। कृपया प्रभारी नर्स से पूछें।",
    "zh": "暂时无法回答。请询问当班护士。",
}


def could_not_answer(lang_tag="en-AU"):
    return COULD_NOT_ANSWER.get((lang_tag or "en").split("-")[0], COULD_NOT_ANSWER["en"])
