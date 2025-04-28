import os
import asyncio
import requests

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from startup import load_models
from retrieval import get_reranked_law_articles, get_reranked_case_chunks
from logger import get_logger

logger = get_logger("bot")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_2")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
dp = Dispatcher(storage=MemoryStorage())

LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "deepseek/deepseek-r1:free"
# MODEL_ID = "deepseek/deepseek-r1-distill-llama-70b:free"
# MODEL_ID = "qwen/qwen-2.5-72b-instruct:free"
# MODEL_ID = "deepseek/deepseek-chat-v3-0324:free"


def escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters."""
    return (
        text.replace("\\", "\\\\")
            .replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("~", "\\~")
            .replace("`", "\\`")
            .replace(">", "\\>")
            .replace("#", "\\#")
            .replace("+", "\\+")
            .replace("-", "\\-")
            .replace("=", "\\=")
            .replace("|", "\\|")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace(".", "\\.")
            .replace("!", "\\!")
    )


# /start handler
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Добро пожаловать\\! Начните консультацию, задав вопрос или описав ваш случай\\."
    )


# Main message handler
@dp.message()
async def message_handler(message: Message):
    query_text = message.text

    law_docs = await asyncio.to_thread(get_reranked_law_articles, query_text, embedder, reranker, client)
    case_docs = await asyncio.to_thread(get_reranked_case_chunks, query_text, embedder, reranker, client)

    law_texts = [escape_md(doc["text"]) for doc in law_docs]
    case_texts = [escape_md(doc["text"]) for doc in case_docs]

    system_prompt = {
        "role": "system",
        "content": (
            "Ты виртуальный ассистент\\-юрист для пользователей из Российской Федерации\\. "
            "Твоя задача — давать точные и обоснованные ответы, ссылаясь на законы и судебную практику, "
            "где это уместно\\. Используй только релевантные источники при ответе\\.\n\n"
            "\\*Потенциально подходящие законы\\*:\n"
            + "\n".join(law_texts)
            + "\n\n"
            "\\*Потенциально подходящие судебные решения\\*:\n"
            + "\n".join(case_texts)
            + "\n\n"
            "Если ссылаешься на закон или судебное решение, обязательно указывай источник \\(после \\[Ссылка на \\...\\]\\), "
            "чтобы пользователь мог самостоятельно его изучить\\! "
            "Если источник не подходит по смыслу к вопросу пользователя, или ты сомневаешься в нем, не используй такой источник\\! "
            "НЕ ИСПОЛЬЗУЙ АНГЛИЙСКИЙ ЯЗЫК В СВОИХ ОТВЕТАХ, ЕСЛИ В ЭТОМ НЕТ НЕОБХОДИМОСТИ\\. "
        ),
    }

    messages = [
        system_prompt,
        {"role": "user", "content": escape_md(query_text)}
    ]

    response_text = await query_llm(messages)
    await message.answer(escape_md(response_text))


# LLM API call
async def query_llm(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "top_p": 1,
        "temperature": 0.0,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "repetition_penalty": 1,
        "top_k": 0,
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "Ответ не получен.")
    except Exception as e:
        logger.exception("Exception during LLM request")
        return "Техническая ошибка\\. Попробуйте позже\\."


# Bot startup
async def main():
    global embedder, reranker, client
    embedder, reranker, client = load_models()
    logger.info("Models loaded. Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Bot starting...")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
