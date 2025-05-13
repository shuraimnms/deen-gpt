from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import re
import difflib
from googletrans import Translator

app = Flask(__name__)
CORS(app)

# 📁 Load only Sahih Bukhari Hadiths
HADITH_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "deen_gpt_model", "hadith-json", "bukhari.json"))
try:
    with open(HADITH_FILE, "r", encoding="utf-8") as f:
        hadith_data = json.load(f)
    bukhari_hadiths = hadith_data.get("hadiths", [])
except Exception as e:
    print(f"Error loading Hadith file: {e}")
    bukhari_hadiths = []

# 📚 Predefined chatbot replies
convo_replies = {
    "assalamu alaikum": "Wa Alaikumussalam wa Rahmatullah! 🌙",
    "assalamualaikum": "Wa Alaikumussalam wa Rahmatullah! 🌙",
    "salaam": "Wa Alaikumussalam wa Rahmatullah!",
    "kahiriyath": "alhamdulillah! How i can hep you? 😊",
  "how are you": "Alhamdulillah, I am good! How about you? 😊",
  "jazakallah": "Wa iyyakum! May Allah reward you too 🤲",
  "jazakallah khair": "Wa iyyakum. May Allah bless you with khair in both worlds 🤍",
  "alhamdulillah": "Alhamdulillah! All praise is due to Allah 🌟",
  "subhanallah": "SubhanAllah! Glory be to Allah 🌌",
  "mashallah": "MashaAllah! May Allah preserve it from evil 👀🤲",
  "inshallah": "InshaAllah! If Allah wills 🕊️",
  "astaghfirullah": "Astaghfirullah! May Allah forgive us all 🙏",
  "ameen": "Ameen Ya Rabb! 🤲",
  "ya allah": "Call upon Him with sincerity. He is As-Sami', the All-Hearing 🕊️",
  "what is islam": "Islam is submission to the will of Allah, through Tawheed, Salah, Zakah, Fasting, and Hajj ☪️",
  "who is allah": "Allah is the One and Only God, Eternal and Absolute, the Creator of all things 🌍",
  "quran": "The Quran is the final revelation from Allah, a guidance for mankind 📖",
  "hadith": "Hadith are the sayings, actions, and approvals of Prophet Muhammad ﷺ 🕋",
  "prophet muhammad": "Prophet Muhammad ﷺ is the last messenger of Allah, a mercy to mankind 💖",
  "peace be upon him": "Peace and blessings be upon him ﷺ",
  "dua": "Make dua sincerely, and know that Allah is always near 🤲",
  "what is dua": "Dua is a personal supplication, a direct connection with Allah 🕋",
  "can you make dua for me": "Of course! May Allah grant you peace, mercy, and success in both worlds 🤍 Ameen!",
  "i am sad": "Turn to Allah. Verily, in the remembrance of Allah do hearts find rest ❤️ (Qur’an 13:28)",
  "i am happy": "Alhamdulillah! May Allah increase your joy and keep you grateful 😊",
  "i need help": "Never lose hope in the mercy of Allah. He is always with the patient 🤲",
  "what is tawheed": "Tawheed is the belief in the Oneness of Allah – the essence of Islam ☝️",
  "what is shirk": "Shirk is associating partners with Allah. It is the gravest sin in Islam 🚫",
  "what is salah": "Salah is the five daily prayers – a pillar of Islam and our connection to Allah 🕌",
  "what is zakah": "Zakah is obligatory charity – purifying your wealth and helping those in need 💰",
  "what is fasting": "Fasting (sawm) is abstaining from food, drink, and sin from dawn to dusk in Ramadan 🌙",
  "what is hajj": "Hajj is the pilgrimage to Makkah once in a lifetime if able – a symbol of unity and submission 🕋",
  "ramadan": "Ramadan is the month of mercy, fasting, and getting closer to Allah 🌙",
  "eid mubarak": "Eid Mubarak! Taqabbalallahu minna wa minkum! 🌸🎉",
  "who created me": "Allah created you in the best form and gave you purpose 🌟 (Qur’an 95:4)",
  "what is the purpose of life": "To worship Allah alone and live righteously (Qur’an 51:56) 🕊️",
  "tell me hadith": "“The best among you are those who have the best manners and character.” – Prophet Muhammad ﷺ",
  "tell me a quran verse": "“Indeed, with hardship [will be] ease.” – Qur’an 94:6 💫",
  "how to be a good muslim": "Pray regularly, follow the Sunnah, do good deeds, and avoid sin 🌼",
  "how to make wudu": "Wash hands, mouth, nose, face, arms, head, ears, and feet – in order 🧼🕌",
  "how to pray": "Stand, recite Surah Fatiha, perform ruku and sujood – maintain khushu (focus) 🕋",
  "can you teach me islam": "Yes! Ask anything. I'm here to help you learn about Islam, inshaAllah 📚",
  "what is the meaning of bismillah": "Bismillah means 'In the name of Allah' – said before doing anything important ✨",
  "what is halal": "Halal means permissible in Islam – including food, actions, and lifestyle ✅",
  "what is sunnah": "Sunnah is the way of Prophet Muhammad ﷺ – his actions, words, and guidance 🕋",
  "can non muslims become muslim": "Yes, Islam is for all humanity. Anyone can embrace Islam by declaring the Shahada ☪️",
  "how to become muslim": "Say with sincerity: 'Ashhadu alla ilaha illallah wa ashhadu anna Muhammadan rasoolullah' ✨",
  "i want to become muslim": "MashaAllah! May Allah guide you and bless your journey of faith 🤍",
  "can you recite a dua": "Sure! 'رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ' – Ameen!",
  "i love islam": "MashaAllah! Islam is a beautiful way of life 💚",
  "thank you": "You're welcome! May Allah bless you 🌸",
  "shukran": "Afwan! May Allah accept from us and you 🤲",
  "goodbye": "Ma'assalama! May Allah protect you always 🌙",
  "see you later": "InshaAllah! Stay blessed and remember Allah 🤍",
}

# 🔎 Helper functions
def normalize(text):
    return text.lower().strip()

def fuzzy_match(query, choices):
    return difflib.get_close_matches(query, choices, n=1, cutoff=0.6)

def search_conversation(text):
    query = normalize(text)
    match = fuzzy_match(query, convo_replies.keys())
    return convo_replies.get(match[0]) if match else None

def extract_hadith_id(text):
    corrected_text = correct_spelling(text)
    match = re.search(r"(bukhari)[^\d]*(\d+)", corrected_text, re.IGNORECASE)
    return int(match.group(2)) if match else None

def search_by_id(hadith_id):
    for h in bukhari_hadiths:
        if h.get("id") == hadith_id or h.get("idInBook") == hadith_id:
            eng = h.get("english", {})
            return {
                "id": h.get("id", hadith_id),
                "book": "Bukhari",
                "arabic": h.get("arabic", "").strip(),
                "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip()
            }
    return None

def search_keywords(query):
    query = normalize(correct_spelling(query))
    keywords = query.split()
    results = []

    for h in bukhari_hadiths:
        eng = h.get("english", {})
        text = f"{eng.get('narrator', '')} {eng.get('text', '')}".lower()
        score = sum(1 for word in keywords if word in text) / len(keywords)
        if score > 0.3:
            results.append({
                "id": h.get("id"),
                "book": "Bukhari",
                "arabic": h.get("arabic", "").strip(),
                "english": f"{eng.get('narrator', '')} {eng.get('text', '')}".strip(),
                "score": score
            })

    return sorted(results, key=lambda x: -x["score"])[:5]

def correct_spelling(user_input):
    words = re.findall(r'\w+', user_input.lower())
    corrected_words = []
    vocab = ["bukhari", "hadith", "buqari", "sahih", "bukari", "bukhaari", "hadess", "hadees", "hadeeth"]

    for word in words:
        corrected = fuzzy_match(word, vocab)
        corrected_words.append(corrected[0] if corrected else word)

    return " ".join(corrected_words)

# 🌐 Translate using Google Translator
def translate_to_language(text, lang_code='ur'):
    try:
        translator = Translator()
        translated = translator.translate(text, src='ar', dest=lang_code)
        return translated.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

# 📖 Load Quran data from JSON file
QURAN_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models", "deen_gpt_model", "quran", "quran.json")
)

def load_quran_data():
    try:
        with open(QURAN_DATA_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Quran file loading error: {e}")
        return {}

quran_data = load_quran_data()

def fetch_quran_verse(chapter, verse, lang_code='ur'):
    chapter_data = quran_data.get(str(chapter), [])
    for item in chapter_data:
        if item.get("verse") == verse:
            arabic = item.get("text", "")
            translated = translate_to_language(arabic, lang_code)
            return {"arabic": arabic, "translation": translated}
    return None

# ✅ Root route for testing
@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "✅ DeenGPT Backend is running!"})

# 🔄 Main chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message", "").strip()
        if not user_input:
            return jsonify({"response": "❌ Please enter a message."})

        # Step 1: Simple greetings
        convo = search_conversation(user_input)
        if convo:
            return jsonify({"response": convo})

        # Step 2: Spell-corrected greetings
        corrected_input = correct_spelling(user_input)
        convo = search_conversation(corrected_input)
        if convo:
            return jsonify({"response": convo})

        # Step 3: Hadith ID
        hadith_id = extract_hadith_id(user_input)
        if hadith_id:
            hadith = search_by_id(hadith_id)
            if hadith:
                lang = "ur"
                user_lower = user_input.lower()
                if 'hindi' in user_lower:
                    lang = "hi"
                elif 'telugu' in user_lower:
                    lang = "te"
                elif 'english' in user_lower:
                    lang = "en"
                elif 'urdu' in user_lower:
                    lang = "ur"

                translated = translate_to_language(hadith["english"], lang)
                return jsonify({
                    "response": f"📖 **{hadith['book']}** | Hadith #{hadith['id']}\n"
                                f"-----------------------------------------\n"
                                f"🕋 **Arabic:**\n{hadith['arabic']}\n"
                                f"-----------------------------------------\n"
                                f"📚 **English:**\n{hadith['english']}\n\n"
                                f"🌙 **{lang.upper()} Translation:**\n{translated}"
                })
            return jsonify({"response": f"❌ Hadith #{hadith_id} not found in Bukhari."})

        # Step 4: Quran verse
        match = re.search(r"(surah|sura)\s*(\d+)\s*(ayah|verse)\s*(\d+)", user_input, re.IGNORECASE)
        if match:
            surah = int(match.group(2))
            ayah = int(match.group(4))
            lang = "ur"
            lower = user_input.lower()
            if 'hindi' in lower:
                lang = "hi"
            elif 'telugu' in lower:
                lang = "te"
            elif 'english' in lower:
                lang = "en"
            elif 'urdu' in lower:
                lang = "ur"

            verse = fetch_quran_verse(surah, ayah, lang)
            if verse:
                return jsonify({
                    "response": f"📖 **Quran - Surah {surah}, Ayah {ayah}**\n"
                                f"-----------------------------------------\n"
                                f"🕋 **Arabic:**\n{verse['arabic']}\n"
                                f"-----------------------------------------\n"
                                f"📚 **Translation ({lang.upper()}):**\n{verse['translation']}"
                })
            return jsonify({"response": f"❌ Quran verse not found for Surah {surah} Ayah {ayah}."})

        # Step 5: Keyword-based hadith search
        matches = search_keywords(user_input)
        if not matches:
            return jsonify({"response": "❌ No relevant Hadith found in Bukhari."})

        blocks = []
        for m in matches:
            blocks.append(
                f"📖 **{m['book']}** | Hadith #{m['id']}\n"
                f"-----------------------------------------\n"
                f"🕋 **Arabic:**\n{m['arabic'] or 'N/A'}\n"
                f"-----------------------------------------\n"
                f"📚 **English:**\n{m['english'] or 'N/A'}"
            )
        return jsonify({"response": "\n\n============================\n\n".join(blocks)})

    except Exception as e:
        print("❌ Server Error:", e)
        return jsonify({"response": "❌ Server error. Please try again."}), 500

# ▶️ Run the app
if __name__ == "__main__":
    app.run(debug=True)
