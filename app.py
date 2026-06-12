import json
import re
import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)



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
You are a helpful AI chatbot.

Always return valid JSON.

Format:

{
  "title": "string",
  "summary": "string",
  "points": ["string"],
  "career": "string"
}

Rules:
- Never return empty JSON fields.
- Always provide a title.
- Always provide a summary.
- If there are no key points, return at least one point.
- If career is not relevant, return an empty string "".
- No markdown.
- No explanations outside JSON.
- For greetings like hi, hello, hey:
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
                "content": str(chat["content"])
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



@app.route("/chat", methods=["POST"])
def chat():

    init_memory()

    data = request.json or {}
    user_message = data.get("message")
    chat_id = data.get("chat_id")

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # SAFE INIT (prevents crash)
    all_sessions = session.get("all_chat_sessions", {})
    saved_chats = session.get("saved_chats", [])

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
        return jsonify({"error": "AI failed"}), 500

    chat_history.append({
        "role": "assistant",
        "content": str(reply)
    })

    all_sessions[chat_id] = chat_history

    session["all_chat_sessions"] = all_sessions
    session["saved_chats"] = saved_chats
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

    init_memory()

    session["current_chat_id"] = chat_id   

    all_sessions = session.get("all_chat_sessions", {})
    messages = all_sessions.get(chat_id, [])

    fixed = []

    for m in messages:
        if m["role"] == "assistant":
            try:
                content = json.loads(m["content"])
            except:
                content = m["content"]
        else:
            content = m["content"]

        fixed.append({
            "role": m["role"],
            "content": content
        })

    return jsonify({"messages": fixed})

@app.route("/new-chat")
def new_chat():

    chat_id = str(uuid.uuid4())

 
    all_sessions = session.get("all_chat_sessions", {})
    saved_chats = session.get("saved_chats", [])


    all_sessions[chat_id] = []



    session["all_chat_sessions"] = all_sessions
    session["saved_chats"] = saved_chats
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