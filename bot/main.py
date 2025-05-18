import os
import re
import aiohttp
import asyncio

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
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "local")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "deepseek/deepseek-r1:free"


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Добро пожаловать! Начните консультацию, задав вопрос или описав ваш случай."
    )


@dp.message()
async def message_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} sent a message. Starting async task...")

    try:
        # Respond immediately
        wait_msg = await message.answer(
            "Генерирую ответ, пожалуйста подождите несколько минут..."
        )

        # Run logic in background to avoid blocking the bot
        asyncio.create_task(handle_query(message, wait_msg))

    except Exception as e:
        logger.exception(f"Immediate failure for user {user_id}")
        await message.answer("Техническая ошибка, пожалуйста повторите попытку позже.")


async def handle_query(message: Message, wait_msg: Message):
    user_id = message.from_user.id
    try:
        query_text = message.text
        global embedder, reranker, client

        law_docs = await get_reranked_law_articles(
            query=query_text,
            embedder=embedder,
            reranker=reranker,
            client=client,
            inference_backend=INFERENCE_BACKEND,
            remote_reranker_model="BAAI/bge-reranker-v2-m3",
        )

        case_docs = await get_reranked_case_chunks(
            query=query_text,
            embedder=embedder,
            reranker=reranker,
            client=client,
            inference_backend=INFERENCE_BACKEND,
            remote_reranker_model="BAAI/bge-reranker-v2-m3",
        )

        law_texts = [doc["text"] for doc in law_docs]
        case_texts = [doc["text"] for doc in case_docs]

        system_prompt = {
            "role": "system",
            "content": (
                "Ты виртуальный ассистент-юрист для пользователей из Российской Федерации. "
                "Твоя задача — давать точные и обоснованные ответы, ссылаясь на законы и судебную практику, "
                "где это уместно\. Используй только релевантные предоставленные источники при ответе.\n\n"
                "Потенциально подходящие законы:\n" + "\n".join(law_texts) + "\n\n"
                "Потенциально подходящие судебные решения:\n"
                + "\n".join(case_texts)
                + "\n\n"
                "Если ссылаешься на закон или судебное решение, обязательно указывай источник [Ссылка на ...](url), "
                "чтобы пользователь мог самостоятельно его изучить! "
                "Если источник не подходит по смыслу к вопросу пользователя, или ты сомневаешься в нем, не используй такой источник!\n"
                "Используй только предоставленные источники, не добавляй свои собственные ссылки на законы или судебные решения.\n"
                "Если не знаешь ответа на вопрос, напиши, что не можешь ответить.\n"
                "Если вопрос пользователя не связян с юридической помощью, откажись от ответа.\n"
                'Сгенерируй ответ для Telegram-бота, используя HTML разметку: <b>жирный</b>, <i>курсив</i>, <a href="ссылка">текст ссылки</a>. Не используй другие теги. Не используй Markdown.\n'
                "Не используй английский язык в своих ответах, если в этом нет необходимости!"
            ),
        }

        messages = [system_prompt, {"role": "user", "content": query_text}]
        response_text = await query_llm(messages)

        # Replace waiting message with the response
        chunks = split_html_message(response_text)

        # Edit first message
        await bot.edit_message_text(
            chat_id=wait_msg.chat.id,
            message_id=wait_msg.message_id,
            text=chunks[0],
        )

        # Send remaining parts
        for chunk in chunks[1:]:
            await bot.send_message(chat_id=wait_msg.chat.id, text=chunk)

    except Exception as e:
        logger.exception(f"Failed to handle message from user {user_id}")
        try:
            await bot.edit_message_text(
                chat_id=wait_msg.chat.id,
                message_id=wait_msg.message_id,
                text="Техническая ошибка, пожалуйста повторите попытку позже.",
            )
        except Exception as edit_error:
            logger.error(f"Couldn't edit wait message: {edit_error}")


async def query_llm(messages):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
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
        async with aiohttp.ClientSession() as session:
            async with session.post(LLM_API_URL, headers=headers, json=payload) as resp:
                result = await resp.json()
                return (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "Ответ не получен.")
                )
    except Exception as e:
        logger.exception("Exception during LLM request")
        return "Техническая ошибка, пожалуйста повторите попытку позже."


def split_html_message(text: str, max_len: int = 4096):
    # Convert <br> to newline
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Allowed tags in Telegram HTML parse mode
    allowed_tags = {"b", "i", "u", "s", "a", "code", "pre"}

    # Remove disallowed tags
    def clean_tags(match):
        tag = match.group(1)
        tag_name = re.split(r"\s|>", tag)[0].lower()
        if tag_name in allowed_tags or tag_name.startswith("a href="):
            return f"<{tag}>"
        return ""

    def clean_closing_tags(match):
        tag = match.group(1)
        if tag.lower() in allowed_tags:
            return f"</{tag}>"
        return ""

    # Remove unsupported opening tags
    text = re.sub(r"<([^/\s>]+[^>]*)>", clean_tags, text)
    # Remove unsupported closing tags
    text = re.sub(r"</([^>]+)>", clean_closing_tags, text)

    chunks = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len

        chunk = text[:split_at].strip()

        # Detect opened but unclosed tags
        open_tags = re.findall(r"<(b|i|u|s|a|code|pre)(?:\s[^>]*)?>", chunk)
        close_tags = re.findall(r"</(b|i|u|s|a|code|pre)>", chunk)

        tag_stack = []
        for tag in open_tags:
            name = tag.split()[0]  # normalize
            tag_stack.append(name)
        for tag in close_tags:
            if tag in tag_stack:
                tag_stack.remove(tag)

        for tag in reversed(tag_stack):
            chunk += f"</{tag}>"

        chunks.append(chunk)

        # Add back the unclosed tags for the next chunk
        reopen = "".join([f"<{tag}>" for tag in tag_stack])
        text = reopen + text[split_at:].strip()

    chunks.append(text)
    return chunks


async def main():
    global embedder, reranker, client
    embedder, reranker, client = load_models()
    logger.info("Models loaded. Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logger.info("Bot starting...")
    logger.info("Qdrant container is running.")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
