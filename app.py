import json
import re
import os
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
    if "chat_history" not in session:
        session["chat_history"] = []



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



def get_ai_response(message):

    init_memory()
    chat_history = session.get("chat_history", [])

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
        messages.append(chat)

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.5
    )

    content = response.choices[0].message.content.strip()

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": content})

    session["chat_history"] = chat_history[-10:]

    return clean_json(content)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/chatbot")
def chatbot():
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():

    try:
        user_message = request.json.get("message")

        reply = get_ai_response(user_message)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({
            "reply": {
                "title": "Error",
                "summary": str(e),
                "points": [],
                "career": ""
            }
        })


if __name__ == "__main__":
    app.run(debug=True)