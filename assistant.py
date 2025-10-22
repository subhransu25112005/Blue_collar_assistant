import io, base64, threading, webbrowser, os, tempfile, time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from deep_translator import GoogleTranslator
import google.generativeai as genai
import pyttsx3
import concurrent.futures

# ---------- CONFIG ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("❌ Please set GEMINI_API_KEY environment variable first.")

genai.configure(api_key=GEMINI_API_KEY)

PORT = int(os.environ.get("PORT", 5000))
ROOT_DIR = Path(__file__).parent.resolve()
URL = f"http://127.0.0.1:{PORT}/"

# ---------- FLASK APP ----------
app = Flask(__name__, static_url_path='', static_folder=str(ROOT_DIR))
CORS(app)

# ---------- THREAD POOL ----------
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# ---------- KEEP GEMINI MODEL READY ----------
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# ---------- SAFE & FAST TTS ----------
def text_to_speech_base64(text, lang="en"):
    """Creates a new pyttsx3 engine each call (no lockups)."""
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = tmp_file.name
    tmp_file.close()

    def _speak():
        local_engine = pyttsx3.init()
        local_engine.setProperty("rate", 170)
        try:
            local_engine.save_to_file(text, tmp_path)
            local_engine.runAndWait()
        finally:
            local_engine.stop()

    future = executor.submit(_speak)
    future.result(timeout=10)

    with open(tmp_path, "rb") as f:
        audio_data = f.read()
    os.remove(tmp_path)

    return base64.b64encode(audio_data).decode("utf-8")

# ---------- CHAT ROUTE ----------
@app.route("/chat", methods=["POST"])
def chat():
    start_time = time.time()

    data = request.get_json(force=True)
    user_text = data.get("text", "").strip()
    lang = data.get("lang", "en")

    if not user_text:
        return jsonify({"error": "No text provided"}), 400

    # Translate Hindi → English if needed
    processed = user_text
    if lang == "hi":
        try:
            processed = GoogleTranslator(source="auto", target="en").translate(user_text)
        except Exception:
            pass

    system_prompt = (
        "You are a polite, helpful AI assistant for blue-collar workers. "
        "Give short, clear, friendly answers about skills, jobs, and guidance."
    )

    try:
        response = gemini_model.generate_content(f"{system_prompt}\nUser: {processed}")
        reply_en = response.text.strip()
    except Exception as e:
        return jsonify({"error": f"Gemini API failed: {e}"}), 500

    # Translate English → Hindi if needed
    reply = reply_en
    if lang == "hi":
        try:
            reply = GoogleTranslator(source="en", target="hi").translate(reply_en)
        except Exception:
            pass

    # Text-to-Speech
    try:
        audio_b64 = text_to_speech_base64(reply, lang)
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500

    duration = round(time.time() - start_time, 2)
    print(f"✅ Reply ready in {duration}s")

    return jsonify({"reply": reply, "audio_base64": audio_b64, "response_time": duration})

# ---------- ROUTES ----------
@app.route("/")
def index():
    return send_from_directory(str(ROOT_DIR), "index.html")

@app.route("/assistant_icon.png")
def icon():
    icon_path = ROOT_DIR / "assistant_icon.png"
    if icon_path.exists():
        return send_from_directory(str(ROOT_DIR), "assistant_icon.png")
    transparent = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgXr4XxkAAAAASUVORK5CYII="
    )
    return (transparent, 200, {"Content-Type": "image/png"})

# ---------- AUTO OPEN ----------
def open_browser():
    try:
        webbrowser.open_new_tab(URL)
    except Exception:
        pass

if __name__ == "_main_":
    threading.Timer(1.0, open_browser).start()
    print(f"🚀 Running Blue Collar Assistant at {URL}")
    app.run(host="0.0.0.0", port=PORT)