import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"
SYSTEM_INSTRUCTION = "You are a helpful assistant. Always respond in the same language the user writes in."
user_histories = {}

def get_history(user_id):
    return user_histories.setdefault(user_id, [])

def add_to_history(user_id, role, text):
    get_history(user_id).append(types.Content(role=role, parts=[types.Part(text=text)]))

async def start(update, context):
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("سلام! من یه دستیار هوشمندم. هر چیزی بخوای بپرس!\n\nاز /clear برای پاک کردن تاریخچه استفاده کن.")

async def clear(update, context):
    user_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("تاریخچه پاک شد!")

async def handle_message(update, context):
    user = update.effective_user
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    add_to_history(user.id, "user", user_text)
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=get_history(user.id),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, max_output_tokens=8192),
        )
        reply = response.text or "نتونستم جواب بدم."
        add_to_history(user.id, "model", reply)
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i+4096])
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error("Error: %s", e)
        get_history(user.id).pop()
        await update.message.reply_text("خطایی پیش اومد، دوباره امتحان کن.")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
