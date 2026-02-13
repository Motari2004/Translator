from flask import Flask, render_template, request, jsonify
import http.client
import json
import os
from datetime import datetime

app = Flask(__name__)

# Get API key from environment variable (Render / .env / secrets)
API_KEY = os.environ.get("RAPIDAPI_KEY")
API_HOST = "deep-translate1.p.rapidapi.com"

if not API_KEY:
    print("WARNING: RAPIDAPI_KEY environment variable is not set!")

# Supported languages (you can expand this list)
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "sw": "Swahili",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "ru": "Russian",
    "hi": "Hindi",
}

# In-memory recent translations (max 5) — for demo only
# In real production → use Redis, SQLite, or Flask-Session
recent_translations = []


def arabic_to_latin(arabic_text):
    """Very basic Arabic → Latin transliteration"""
    mapping = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h",
        "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s",
        "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
        "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m",
        "ن": "n", "ه": "h", "و": "w", "ي": "y", "ء": "'", "ى": "a",
        "ة": "h", "؟": "?", "،": ",", "!": "!", "أ": "a", "إ": "i",
        "آ": "aa", "ؤ": "u", "ئ": "y", " ": " "
    }
    return "".join(mapping.get(c, c) for c in arabic_text)


@app.route('/')
def home():
    return render_template(
        'index.html',
        languages=LANGUAGES,
        recent_translations=recent_translations
    )


@app.route('/translate', methods=['POST'])
def translate():
    if not API_KEY:
        return jsonify({"error": "Server configuration error: API key missing"}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        text = data.get('text', '').strip()
        source_lang = data.get('source_lang')
        target_lang = data.get('target_lang')

        if not text:
            return jsonify({"error": "Please enter some text to translate"}), 400
        if not source_lang or not target_lang:
            return jsonify({"error": "Source and target languages are required"}), 400
        if source_lang not in LANGUAGES or target_lang not in LANGUAGES:
            return jsonify({"error": "Unsupported language selected"}), 400

        conn = http.client.HTTPSConnection(API_HOST)
        
        payload = json.dumps({
            "q": text,
            "source": source_lang,
            "target": target_lang
        })

        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': API_HOST,
            'Content-Type': 'application/json'
        }

        conn.request("POST", "/language/translate/v2", payload, headers)
        res = conn.getresponse()
        response_data = res.read().decode("utf-8")

        if res.status != 200:
            return jsonify({
                "error": f"API returned status {res.status}",
                "details": response_data
            }), 502

        try:
            result = json.loads(response_data)
            translated_text = result.get('data', {}) \
                                  .get('translations', {}) \
                                  .get('translatedText', '')
            
            if not translated_text:
                translations = result.get('data', {}).get('translations', [])
                if translations and isinstance(translations, list):
                    translated_text = translations[0].get('translatedText', '')
        except Exception as e:
            return jsonify({
                "error": "Failed to parse translation response",
                "details": str(e)
            }), 500

        if not translated_text:
            return jsonify({"error": "No translation received from API"}), 500

        display_text = translated_text
        if target_lang == "ar":
            display_text = arabic_to_latin(translated_text)

        recent_translations.insert(0, {
            "original": text,
            "translated": display_text,
            "target": LANGUAGES.get(target_lang, target_lang),
            "time": datetime.now().strftime("%H:%M")
        })

        if len(recent_translations) > 5:
            recent_translations.pop()

        return jsonify({
            "translated_text": display_text,
            "original_api_text": translated_text  # useful for debugging
        })

    except Exception as e:
        return jsonify({
            "error": "Translation service error",
            "details": str(e)
        }), 500


# ────────────────────────────────────────────────
#   Port & Server Configuration (Local vs Production)
# ────────────────────────────────────────────────
if __name__ == "__main__":
    # Local development only — use high port to avoid conflicts
    port = int(os.environ.get("PORT", 50000))          # Default 50000 locally
    app.run(
        debug=True,
        host="0.0.0.0",
        port=port,
        use_reloader=True
    )