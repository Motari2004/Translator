import os
import http.client
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- SMART CONFIGURATION ---
# 1. API KEY: Looks for Render environment variable first, falls back to your string for local.
API_KEY = os.environ.get("API_KEY", "a6fedd1327msh189f345487b21e0p195c04jsn184073405e8b")
API_HOST = "deep-translate1.p.rapidapi.com"

# Supported languages
LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "sw": "Swahili", "it": "Italian", "pt": "Portuguese", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese", "ar": "Arabic"
}

recent_translations = []

def arabic_to_latin(arabic_text):
    mapping = {
        "ا":"a","ب":"b","ت":"t","ث":"th","ج":"j","ح":"h",
        "خ":"kh","د":"d","ذ":"dh","ر":"r","ز":"z","س":"s",
        "ش":"sh","ص":"s","ض":"d","ط":"t","ظ":"z","ع":"a",
        "غ":"gh","ف":"f","ق":"q","ك":"k","ل":"l","م":"m",
        "ن":"n","ه":"h","و":"w","ي":"y","ء":"'", "ى":"a",
        "ة":"h","؟":"?","،":",","!":"!"
    }
    return "".join([mapping.get(char, char) for char in arabic_text])

@app.route('/')
def home():
    return render_template('index.html', languages=LANGUAGES, recent_translations=recent_translations)

@app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    text, src, tgt = data.get('text'), data.get('source_lang'), data.get('target_lang')

    if not all([text, src, tgt]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = http.client.HTTPSConnection(API_HOST)
        payload = json.dumps({"q": text, "source": src, "target": tgt})
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': API_HOST,
            'Content-Type': "application/json"
        }
        conn.request("POST", "/language/translate/v2", payload, headers)
        res = conn.getresponse()
        result = json.loads(res.read().decode("utf-8"))

        # Extract nested translation text
        translated_text = result['data']['translations']['translatedText']

        if tgt == "ar":
            translated_text = arabic_to_latin(translated_text)

        recent_translations.insert(0, {
            "original": text,
            "translated": translated_text,
            "target": LANGUAGES.get(tgt, tgt)
        })
        if len(recent_translations) > 5: recent_translations.pop()

        return jsonify({"translated_text": translated_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # --- ENVIRONMENT DETECTION ---
    # If 'PORT' exists (Render), use it. Otherwise (Local), use 5000.
    port = int(os.environ.get("PORT", 5000))
    # Local: debug=True helps you see errors. 
    # Prod: host='0.0.0.0' is required for Render to see the app.
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get("PORT") is None))