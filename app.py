import os
import http.client
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- CONFIGURATION ---
API_KEY = os.environ.get("RAPIDAPI_KEY", "a6fedd1327msh189f345487b21e0p195c04jsn184073405e8b")
API_HOST = "deep-translate1.p.rapidapi.com"

LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "sw": "Swahili", "it": "Italian", "pt": "Portuguese", "ja": "Japanese",
    "ko": "Korean", "zh": "Chinese (Simplified)", "ar": "Arabic", 
    "ru": "Russian", "hi": "Hindi"
}

recent_translations = []

# --- PING & MONITORING ROUTES ---

@app.route('/ping')
def internal_ping():
    """Internal Ping: Used by Render/UptimeRobot to keep the app awake."""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "message": "I'm awake!"
    }), 200

@app.route('/ping-api')
def external_ping():
    """External Ping: Verifies the connection to Deep Translate API."""
    try:
        start_time = time.time()
        conn = http.client.HTTPSConnection(API_HOST, timeout=5)
        conn.request("GET", "/language/translate/v2/languages", headers={'x-rapidapi-key': API_KEY})
        res = conn.getresponse()
        latency = round((time.time() - start_time) * 1000, 2)
        
        if res.status == 200:
            return jsonify({"api_status": "connected", "latency_ms": latency}), 200
        else:
            return jsonify({"api_status": "error", "http_code": res.status}), 502
    except Exception as e:
        return jsonify({"api_status": "unreachable", "error": str(e)}), 500

# --- TRANSLATION LOGIC ---

def arabic_to_latin(arabic_text):
    mapping = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h",
        "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s",
        "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
        "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "m": "m",
        "ن": "n", "ه": "h", "و": "w", "ي": "y", "ء": "'", "ى": "a",
        "ة": "h", "؟": "?", "،": ",", "!": "!", "أ": "a", "إ": "i",
        "آ": "aa", "ؤ": "u", "ئ": "y", " ": " "
    }
    return "".join(mapping.get(c, c) for c in arabic_text)

@app.route('/')
def home():
    return render_template('index.html', languages=LANGUAGES, recent_translations=recent_translations)

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid JSON"}), 400

    text = data.get('text', '').strip()
    src, tgt = data.get('source_lang'), data.get('target_lang')

    if not text or not src or not tgt:
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = http.client.HTTPSConnection(API_HOST)
        payload = json.dumps({"q": text, "source": src, "target": tgt})
        headers = {
            'x-rapidapi-key': API_KEY,
            'x-rapidapi-host': API_HOST,
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/language/translate/v2", payload, headers)
        res = conn.getresponse()
        
        result = json.loads(res.read().decode("utf-8"))
        translated_text = result['data']['translations']['translatedText']
        if isinstance(translated_text, list): translated_text = translated_text[0]

        display_text = arabic_to_latin(translated_text) if tgt == "ar" else translated_text

        recent_translations.insert(0, {
            "original": text,
            "translated": display_text,
            "target": LANGUAGES.get(tgt, tgt),
            "time": datetime.now().strftime("%H:%M")
        })
        if len(recent_translations) > 5: recent_translations.pop()

        return jsonify({"translated_text": display_text})

    except Exception as e:
        return jsonify({"error": "Translation failed", "details": str(e)}), 500

if __name__ == "__main__":
    # Works for Render (10000) and Local (50000)
    port = int(os.environ.get("PORT", 50000))
    app.run(host="0.0.0.0", port=port, debug=(os.environ.get("PORT") is None))