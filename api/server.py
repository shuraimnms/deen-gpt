from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, re, difflib, socket
from collections import defaultdict

app = Flask(__name__, static_folder='../static', template_folder='..')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HADITH_DIR = os.path.join(BASE_DIR, "models", "deen_gpt_model", "hadith-json")
QURAN_FILE = os.path.join(BASE_DIR, "models", "deen_gpt_model", "quran.json")

# Load Data
hadith_books = {}
quran_data = []
cache = defaultdict(list)

# Load Hadith
for file in os.listdir(HADITH_DIR):
    if file.endswith(".json"):
        book_name = file.replace(".json", "").lower()
        with open(os.path.join(HADITH_DIR, file), "r", encoding="utf-8") as f:
            hadith_books[book_name] = json.load(f).get("hadiths", [])

# Load Quran
if os.path.exists(QURAN_FILE):
    with open(QURAN_FILE, "r", encoding="utf-8") as f:
        quran_data = json.load(f)

# Conversational Replies
convo_replies = {
   "assalamu alaikum": "Wa Alaikumussalam wa Rahmatullah! 🌙",
    "assalamualaikum": "Wa Alaikumussalam wa Rahmatullah!",
    "salaam": "Wa Alaikumussalam!",
    "walaikum salam": "Wa Alaikumussalam! 😊 Anything else I can assist you with?",
    "how are you": "Alhamdulillah, I am good! How about you? 😊",
    "khairiyyath": "Alhamdulillah! Sab khair hai. Aap kaise ho?",
    "jazakallah": "Wa iyyakum! May Allah reward you too 🤲",
    "thanks": "You're welcome! 😊",
    "shukran": "Afwan!",
    "hello": "Assalamu Alaikum wa Rahmatullah!",
    "hi": "Assalamu Alaikum!",
    "salam": "Wa Alaikumussalam wa Rahmatullah!",
    "asslamualikum": "Wa Alaikumussalam wa Rahmatullah!",
    "good morning": "Good morning! May your day be filled with blessings. 🌅",
    "good evening": "Good evening! May your evening be peaceful and full of Barakah. 🌙",
    "good night": "Good night! May Allah protect you through the night. 🌙",
    "what is hadith": "Hadith are the sayings, actions, and approvals of Prophet Muhammad ﷺ. Would you like to read one?",
    "who is prophet": "Prophet Muhammad ﷺ is the final messenger of Islam. Would you like a Hadith about him?"
}

def normalize(text): return text.lower().strip()

def search_conversation(text):
    query = normalize(text)
    match = difflib.get_close_matches(query, convo_replies.keys(), n=1, cutoff=0.6)
    return convo_replies.get(match[0]) if match else None

def extract_book_and_id(text):
    match = re.search(r"(bukhari|muslim|tirmidhi|nasai|abudawood|ibnmajah|ahmad)[^\d]*(\d+)", text, re.IGNORECASE)
    return (match.group(1).lower(), int(match.group(2))) if match else (None, None)

def search_by_id(book, hadith_id):
    for h in hadith_books.get(book, []):
        if h.get("id") == hadith_id or h.get("idInBook") == hadith_id:
            eng = h.get("english", {})
            return {
                "id": h.get("id", hadith_id),
                "book": book.title(),
                "arabic": h.get("arabic", "").strip(),
                "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip()
            }
    return None

def search_keywords(text):
    text = normalize(text)
    if text in cache: return cache[text]
    keywords = text.split()
    results = []

    for book, entries in hadith_books.items():
        for h in entries:
            eng = h.get("english", {})
            text = f"{eng.get('narrator', '')} {eng.get('text', '')}".lower()
            score = sum(1 for k in keywords if k in text) / len(keywords)
            if score > 0.3:
                results.append({
                    "id": h.get("id"),
                    "book": book.title(),
                    "arabic": h.get("arabic", "").strip(),
                    "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip(),
                    "score": score
                })
    results = sorted(results, key=lambda x: -x["score"])[:5]
    cache[text] = results
    return results

def search_quran(text):
    query = normalize(text)
    match = re.match(r"(\d+):(\d+)", query)
    results = []

    if match:
        surah, ayah = int(match.group(1)), int(match.group(2))
        for verse in quran_data:
            if verse["surah"] == surah and verse["ayah"] == ayah:
                return [{"surah": surah, "ayah": ayah, "arabic": verse["text"], "translation": verse.get("translation", "")}]
    else:
        for verse in quran_data:
            if any(word in verse.get("translation", "").lower() for word in query.split()):
                results.append({
                    "surah": verse["surah"],
                    "ayah": verse["ayah"],
                    "arabic": verse["text"],
                    "translation": verse.get("translation", "")
                })
    return results[:3]

@app.route("/chat", methods=["POST"])
def chat():
    try:
        msg = request.json.get("message", "").strip()
        if not msg:
            return jsonify({"response": "❌ Please say something."})

        convo = search_conversation(msg)
        if convo:
            return jsonify({"response": convo})

        book, hadith_id = extract_book_and_id(msg)
        if book and hadith_id:
            h = search_by_id(book, hadith_id)
            if h:
                return jsonify({"response": (
                    f"📖 **{h['book']}** | Hadith #{h['id']}\n"
                    f"🕋 **Arabic:**\n{h['arabic']}\n\n"
                    f"📚 **English:**\n{h['english']}"
                )})

        matches = search_keywords(msg)
        if matches:
            response = "\n\n---\n\n".join([
                f"📖 **{m['book']}** | Hadith #{m['id']}\n🕋 **Arabic:** {m['arabic']}\n📚 **English:** {m['english']}"
                for m in matches
            ])
            return jsonify({"response": response})

        quran_results = search_quran(msg)
        if quran_results:
            quran_reply = "\n\n".join([
                f"📖 **Surah {v['surah']} : Ayah {v['ayah']}**\n🕋 **Arabic:** {v['arabic']}\n📚 **Translation:** {v['translation']}"
                for v in quran_results
            ])
            return jsonify({"response": quran_reply})

        return jsonify({"response": "❌ No relevant Hadith or Quran verse found."})
    except Exception as e:
        print("Server Error:", e)
        return jsonify({"response": "❌ Server Error"}), 500

@app.route("/books", methods=["GET"])
def list_books():
    return jsonify({"books": list(hadith_books.keys())})

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try: s.bind(('0.0.0.0', port)); return False
        except socket.error: return True

if __name__ == "__main__":
    port = 5000
    while is_port_in_use(port) and port < 5010:
        port += 1
    if port >= 5010:
        print("No available port.")
        exit(1)
    print(f"✅ Running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
