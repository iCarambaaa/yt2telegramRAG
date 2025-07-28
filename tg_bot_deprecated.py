import os
import sqlite3
import openai
from dotenv import load_dotenv
from telegram.ext import Updater, MessageHandler, Filters
import logging
try:
    import yaml
except ImportError:
    raise ImportError("pyyaml is required for prompt loading. Install with: pip install pyyaml")

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "/root/youtube_monitor.db")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("yt2telegramRAG-bot.log"),
        logging.StreamHandler()
    ]
)

def load_prompt():
    prompt_file = os.getenv("TG_BOT_PROMPT_FILE")
    if prompt_file and os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('qa_prompt')
    return None

BOT_PROMPT_TEMPLATE = load_prompt() or (
    "You are a helpful assistant for a YouTube-to-Telegram RAG bot.\n"
    "Use the transcript and previous video summaries to answer user questions concisely and informatively.\n"
    "If the answer is not in the context, say you don't know.\n\n"
    "Context:\n"
    "Latest video transcript:\n{transcript}\n\n"
    "Previous video summaries:\n{summaries}\n\n"
    "User question:\n{question}\n\n"
    "Answer:"
)

def get_context():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT transcript FROM processed_videos ORDER BY published_at DESC LIMIT 1')
        latest_transcript = cursor.fetchone()
        cursor.execute('SELECT summary FROM processed_videos ORDER BY published_at DESC')
        summaries = [row[0] for row in cursor.fetchall()]
        conn.close()
        return latest_transcript[0] if latest_transcript else "", summaries
    except Exception as e:
        logging.error(f"Error fetching context from DB: {e}")
        return "", []

def answer_question(question, transcript, summaries):
    try:
        client = openai.OpenAI(api_key=os.getenv("LLM_PROVIDER_API_KEY"))
        model = os.getenv("OPENAI_MODEL_BOT", "gpt-4-1106-preview")
        prompt = BOT_PROMPT_TEMPLATE.format(transcript=transcript, summaries="\n---\n".join(summaries), question=question)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Answer user questions using the transcript and summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        logging.info("Answer generated and sent.")
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Sorry, I couldn't process your question right now."

def handle_message(update, context):
    try:
        question = update.message.text
        transcript, summaries = get_context()
        answer = answer_question(question, transcript, summaries)
        update.message.reply_text(answer)
    except Exception as e:
        logging.error(f"Telegram bot error: {e}")
        update.message.reply_text("An error occurred. Please try again later.")

def main():
    updater = Updater(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
