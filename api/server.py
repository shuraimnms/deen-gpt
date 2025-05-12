
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import re
import difflib
from collections import defaultdict
import socket

app = Flask(__name__, static_folder='../static', template_folder='..')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Load Hadith books
HADITH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "deen_gpt_model", "hadith-json"))
hadith_books = {}
cache = defaultdict(list)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

# Load JSON files into memory
for file in os.listdir(HADITH_DIR):
    if file.endswith(".json"):
        book_name = file.replace(".json", "").lower()
        with open(os.path.join(HADITH_DIR, file), "r", encoding="utf-8") as f:
            data = json.load(f)
            hadith_books[book_name] = data.get("hadiths", [])

# Simple AI-like conversation replies
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

def normalize(text):
    return text.lower().strip()

def search_conversation(text):
    query = normalize(text)
    match = difflib.get_close_matches(query, convo_replies.keys(), n=1, cutoff=0.6)
    if match:
        return convo_replies.get(match[0])
    return None

def extract_book_and_id(text):
    match = re.search(r"(bukhari|muslim|tirmidhi|nasai|abudawood|ibnmajah|ahmad)[^\d]*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return None, None

def search_by_id(book, hadith_id):
    entries = hadith_books.get(book, [])
    for h in entries:
        if h.get("id") == hadith_id or h.get("idInBook") == hadith_id:
            eng = h.get("english", {})
            return {
                "id": h.get("id", hadith_id),
                "book": book.title(),
                "arabic": h.get("arabic", "").strip(),
                "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip()
            }
    return None

def search_keywords(query):
    query = normalize(query)
    if query in cache:
        return cache[query]

    keywords = query.split()
    results = []

    for book, entries in hadith_books.items():
        for h in entries:
            eng = h.get("english", {})
            combined_text = f"{eng.get('narrator', '')} {eng.get('text', '')}".lower()
            score = sum(1 for word in keywords if word in combined_text) / len(keywords)
            if score > 0.3:
                results.append({
                    "id": h.get("id"),
                    "book": book.title(),
                    "arabic": h.get("arabic", "").strip(),
                    "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip(),
                    "score": score
                })

    results = sorted(results, key=lambda x: -x["score"])[:5]
    cache[query] = results
    return results

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "").strip()
        if not user_input:
            return jsonify({"response": "❌ Please enter a message."})

        # Step 1: Conversational match
        convo = search_conversation(user_input)
        if convo:
            return jsonify({"response": convo})

        # Step 2: Check for Hadith by ID
        book, hadith_id = extract_book_and_id(user_input)
        if book and hadith_id:
            hadith = search_by_id(book, hadith_id)
            if hadith:
                return jsonify({
                    "response": (
                        f"📖 **{hadith['book']}** | Hadith #{hadith['id']}\n"
                        f"-----------------------------------------\n"
                        f"🕋 **Arabic:**\n{hadith['arabic']}\n\n"
                        f"📚 **English:**\n{hadith['english']}"
                    )
                })
            else:
                return jsonify({"response": f"❌ Hadith #{hadith_id} not found in {book.title()}."})

        # Step 3: Keyword match
        matches = search_keywords(user_input)
        if not matches:
            return jsonify({"response": "❌ No relevant Hadith found."})

        reply = []
        for res in matches:
            reply.append(
                f"📖 **{res['book']}** | Hadith #{res['id']}\n"
                f"-----------------------------------------\n"
                f"🕋 **Arabic:**\n{res['arabic']}\n\n"
                f"📚 **English:**\n{res['english']}"
            )

        return jsonify({"response": "\n\n============================\n\n".join(reply)})

    except Exception as e:
        print("❌ Server Error:", e)
        return jsonify({"response": "❌ Server error. Please try again."}), 500

@app.route("/books", methods=["GET"])
def list_books():
    return jsonify({"books": list(hadith_books.keys())})

if __name__ == "__main__":
    port = 5000
    while is_port_in_use(port) and port < 5010:
        port += 1
    
    if port >= 5010:
        print("Could not find an available port between 5000 and 5009")
        exit(1)
        
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
