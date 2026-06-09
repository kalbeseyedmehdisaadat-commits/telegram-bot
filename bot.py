import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are a helpful, friendly, and intelligent assistant. "
    "Always respond in the same language the user writes in. "
    "Be concise but thorough. If the user switches languages, switch with them immediately."
)

user_histories: dict[int, list[types.Content]] = {}


def get_history(user_id: int) -> list[types.Content]:
    return user_histories.setdefault(user_id, [])


def add_to_history(user_id: int, role: str, text: str) -> None:
    history = get_history(user_id)
    history.append(types.Content(role=role, parts=[types.Part(text=text)]))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_histories.pop(user.id, None)
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm powered by Gemini AI. Send me any message and I'll reply intelligently. "
        "I remember our conversation and respond in whatever language you write in.\n\n"
        "Use /clear to reset the conversation history."
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_histories.pop(user.id, None)
await update.message.reply_text("Conversation history cleared. Starting fresh!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_text = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    add_to_history(user.id, "user", user_text)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=get_history(user.id),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=8192,
            ),
        )

        reply = response.text or "I could not generate a response. Please try again."
        add_to_history(user.id, "model", reply)

        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i + 4096])
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error("Gemini error for user %s: %s", user.id, e)
        get_history(user.id).pop()
        await update.message.reply_text(
            "Sorry, something went wrong while generating a response. Please try again."
        )


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started. Polling for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
