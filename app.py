import json
import re
import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv

from flask_session import Session


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

app.config["SESSION_TYPE"] = "filesystem"
Session(app)

all_sessions = {}
saved_chats = []
 
def init_memory():
    session.setdefault("saved_chats", [])
    session.setdefault("all_chat_sessions", {})
    session.setdefault("current_chat_id", None)



def clean_json(text):
    text = text.strip()
    text = re.sub(r"```json|```", "", text)

    try:
        return json.loads(text)
    except:
        return {
            "title": "Response",
            "summary": text,
            "points": [],
            "career": ""
        }





def get_ai_response(chat_history, message):

    try:
        system_prompt = """
You are a chatbot that MUST return ONLY valid JSON.

STRICT RULES:
- Output ONLY JSON (no text, no markdown, no explanation)
- Always use double quotes for keys and strings
- Never use single quotes
- Never return Python dictionary format

Required format:
{
  "title": "...",
  "summary": "...",
  "points": ["...", "..."],
  "career": "..."
}

If greeting:
{
  "title": "Greeting",
  "summary": "Hello! How can I help you today?",
  "points": ["Ask me anything."],
  "career": ""
}
"""
        messages = [{"role": "system", "content": system_prompt}]

        for chat in chat_history:
           messages.append({
    "role": chat["role"],
    "content": chat["content"] if isinstance(chat["content"], str)
    else json.dumps(chat["content"])
})

        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.5
        )

        content = response.choices[0].message.content.strip()

        return clean_json(content)

    except Exception as e:
        print(" AI ERROR:", e)

        return {
            "title": "Error",
            "summary": "AI request failed. Please check server or API key.",
            "points": [],
            "career": ""
        }


@app.route("/")
def home():
    return render_template("home.html")

def safe_session():
    if "all_chat_sessions" not in session:
        session["all_chat_sessions"] = {}
    if "saved_chats" not in session:
        session["saved_chats"] = []
    if "current_chat_id" not in session:
        session["current_chat_id"] = None

@app.route("/chat", methods=["POST"])
def chat():

    init_memory()
    safe_session()

    data = request.json or {}
    user_message = data.get("message")
    chat_id = data.get("chat_id")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    all_sessions = session["all_chat_sessions"]
    saved_chats = session["saved_chats"]

    if not chat_id:
        chat_id = str(uuid.uuid4())

    if chat_id not in all_sessions:
        all_sessions[chat_id] = []

        saved_chats.append({
            "id": chat_id,
            "title": user_message.strip()
        })

    chat_history = all_sessions[chat_id]

    chat_history.append({
        "role": "user",
        "content": user_message
    })

    try:
        reply = get_ai_response(chat_history, user_message)
    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({
            "reply": {
                "title": "Error",
                "summary": "AI failed",
                "points": [],
                "career": ""
            },
            "chat_id": chat_id
        }), 500


    chat_history.append({
        "role": "assistant",
        "content": reply
    })

    session["current_chat_id"] = chat_id

    return jsonify({
        "reply": reply,
        "chat_id": chat_id
    })
@app.route("/history")
def history():
    saved_chats = session.get("saved_chats", [])
    return jsonify(saved_chats)

@app.route("/reset")
def reset():
    session.clear()
    return "cleared"



@app.route("/load-chat/<chat_id>")
def load_chat(chat_id):

    safe_session()

    all_sessions = session["all_chat_sessions"]
    messages = all_sessions.get(chat_id, [])

    return jsonify({
        "messages": messages
    })
@app.route("/new-chat")
def new_chat():

    safe_session()

    chat_id = str(uuid.uuid4())

    session["all_chat_sessions"][chat_id] = []

    session["current_chat_id"] = chat_id

    return jsonify({"chat_id": chat_id})


@app.route("/chatbot")
def chatbot():

    init_memory()


    session.setdefault("saved_chats", [])
    session.setdefault("all_chat_sessions", {})
    session.setdefault("current_chat_id", None)

    return render_template("chat.html")

if __name__ == "__main__":
    app.run(debug=True)