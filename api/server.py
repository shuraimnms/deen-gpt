from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, re, difflib, socket
import requests  # Import requests library
from collections import defaultdict

app = Flask(__name__, static_folder='../static', template_folder='..')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HADITH_DIR = os.path.join(BASE_DIR, "models", "deen_gpt_model", "hadith-json")

# Load Data
hadith_books = {}
cache = defaultdict(list)

# Synonyms map
synonyms = {
    "prophet": "messenger",
    "messenger": "prophet",
    "salat": "namaz",
    "namaz": "salat",
    "duaa": "dua",
    "dua": "duaa",
    "zakat": "charity",
    "charity": "zakat",
    "fasting": "sawm",
    "sawm": "fasting",
    "allah": "god",
    "god": "allah",
}

# Load Hadith
for file in os.listdir(HADITH_DIR):
    if file.endswith(".json"):
        book_name = file.replace(".json", "").lower()
        with open(os.path.join(HADITH_DIR, file), "r", encoding="utf-8") as f:
            hadith_books[book_name] = json.load(f).get("hadiths", [])

# Conversational Responses
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

def expand_synonyms(words):
    expanded = set(words)
    for w in words:
        if w in synonyms:
            expanded.add(synonyms[w])
    return list(expanded)

def search_conversation(text):
    query = normalize(text)
    match = difflib.get_close_matches(query, convo_replies.keys(), n=1, cutoff=0.6)
    return convo_replies.get(match[0]) if match else None

def extract_book_and_id(text):
    match = re.search(r"(bukhari|muslim|tirmidhi|nasai|abudawood|ibnmajah|ahmad)[^\d]*(\d+)", text, re.IGNORECASE)
    return (match.group(1).lower(), int(match.group(2))) if match else (None, None)

def extract_book_name(text):
    match = re.search(r"(bukhari|muslim|tirmidhi|nasai|abudawood|ibnmajah|ahmad)", text, re.IGNORECASE)
    return match.group(1).lower() if match else None

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

def search_by_book(book_name, count=5):
    results = []
    for h in hadith_books.get(book_name, [])[:count]:
        eng = h.get("english", {})
        results.append({
            "id": h.get("id"),
            "book": book_name.title(),
            "arabic": h.get("arabic", "").strip(),
            "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip()
        })
    return results

def search_keywords(text, threshold=0.25):
    text = normalize(text)
    if text in cache: return cache[text]

    words = text.split()
    words = expand_synonyms(words)
    results = []

    for book, entries in hadith_books.items():
        for h in entries:
            eng = h.get("english", {})
            content = f"{eng.get('narrator', '')} {eng.get('text', '')}".lower()
            score = sum(1 for k in words if k in content) / len(words)
            if score > threshold:
                results.append({
                    "id": h.get("id"),
                    "book": book.title(),
                    "arabic": h.get("arabic", "").strip(),
                    "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip(),
                    "score": round(score, 2)
                })
    results = sorted(results, key=lambda x: -x["score"])[:5]
    cache[text] = results
    return results

def search_quran(text):
    query = normalize(text)
    match = re.match(r"(\d+):(\d+)", query)
    results = []

    # API URL for Quran
    quran_api_url = "https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.asad"

    if match:
        surah, ayah = int(match.group(1)), int(match.group(2))
        response = requests.get(quran_api_url.format(surah=surah, ayah=ayah))
        if response.status_code == 200:
            data = response.json()
            verse = data.get("data", {})
            return [{
                "surah": surah,
                "ayah": ayah,
                "arabic": verse.get("text"),
                "translation": verse.get("translation")
            }]
    else:
        words = expand_synonyms(query.split())
        for surah in range(1, 115):
            for ayah in range(1, 100):  # Assumes up to 100 verses per Surah
                response = requests.get(quran_api_url.format(surah=surah, ayah=ayah))
                if response.status_code == 200:
                    data = response.json()
                    verse = data.get("data", {})
                    translation = verse.get("translation", "").lower()
                    if any(word in translation for word in words):
                        results.append({
                            "surah": surah,
                            "ayah": ayah,
                            "arabic": verse.get("text"),
                            "translation": translation
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

        book_name = extract_book_name(msg)
        if book_name:
            hadiths = search_by_book(book_name)
            if hadiths:
                response = "\n\n---\n\n".join([ 
                    f"📖 **{h['book']}** | Hadith #{h['id']}\n🕋 **Arabic:** {h['arabic']}\n📚 **English:** {h['english']}" 
                    for h in hadiths
                ])
                return jsonify({"response": response})

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

@app.route("/search", methods=["GET"])
def search_api():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Missing 'q' parameter"}), 400
    results = search_keywords(query)
    return jsonify({"query": query, "results": results})

@app.route("/books", methods=["GET"])
def list_books():
    return jsonify({"books": list(hadith_books.keys())})

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

if __name__ == "__main__":
    port = 5000
    while is_port_in_use(port) and port < 5010:
        port += 1
    if port >= 5010:
        print("❌ No available port.")
        exit(1)
    print(f"✅ Running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
