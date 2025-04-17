import logging
import requests
import os
import asyncio
import re
from collections import deque

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.markdown import hbold, hitalic, hunderline, hstrikethrough

# Logging setup
logging.basicConfig(level=logging.INFO)

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Bot and Dispatcher setup
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# LLM API settings
LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "deepseek/deepseek-r1-distill-llama-70b:free"

# System prompt (always sent)
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты чатбот-юрист. Ты должен чётко и с ссылками на законодательство или судебную практику РФ "
        "отвечать на вопросы пользователя."
    ),
}

# Max history length
MAX_HISTORY = 10

# User context queue
conversation_context = {}


def markdown_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"__(.*?)__", r"<u>\1</u>", text)
    text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text)
    return text


@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    conversation_context[user_id] = deque(maxlen=MAX_HISTORY)
    await message.answer(
        "Добро пожаловать! Начните консультацию, задав вопрос или описав ваш случай."
    )


@dp.message(Command("newchat"))
async def new_chat_handler(message: Message):
    user_id = message.from_user.id
    conversation_context[user_id] = deque(maxlen=MAX_HISTORY)
    await message.answer("Диалог сброшен. Можете начать новый вопрос.")


@dp.message()
async def message_handler(message: Message):
    user_id = message.from_user.id
    user_input = message.text

    if user_id not in conversation_context:
        conversation_context[user_id] = deque(maxlen=MAX_HISTORY)

    # Add user message to context
    conversation_context[user_id].append({"role": "user", "content": user_input})

    # Combine with system prompt
    messages = [SYSTEM_PROMPT] + list(conversation_context[user_id])

    # Send to LLM
    response_text = await query_llm(messages)

    # Add bot's response to context
    conversation_context[user_id].append(
        {"role": "assistant", "content": response_text}
    )

    await message.answer(markdown_to_html(response_text))


async def query_llm(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "top_p": 1,
        "temperature": 0.8,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "repetition_penalty": 1,
        "top_k": 0,
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            logging.error(f"LLM Error: {result}")
            return "Произошла ошибка. Пожалуйста, попробуйте позже."
    except Exception as e:
        logging.exception("Exception during LLM request")
        return "Техническая ошибка. Попробуйте позже."


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.info("Bot started")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
