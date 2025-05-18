import json
import asyncio
import os
import time
import aiohttp

from bot.startup import load_models
from retrieval import get_reranked_law_articles, get_reranked_case_chunks
from logger import get_logger

INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "local")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "deepseek/deepseek-r1"

logger = get_logger()


def build_system_prompt_rag(law_texts, case_texts):
    return {
        "role": "system",
        "content": (
            "Ты виртуальный ассистент-юрист для пользователей из Российской Федерации. "
            "Твоя задача — давать точные и обоснованные ответы строго на русском языке, "
            "ссылаясь на предоставленные законы и судебную практику, где это уместно.\n"
            "Если ссылаешься на закон или судебное решение, обязательно указывай источник в виде: "
            "'[Название](URL)'\n"
            "Все такие ссылки уже присутствуют в текстах, предоставленных ниже. "
            "Ты должен дословно копировать ссылки из этих текстов, не придумывать свои и не изменять URL.\n"
            "Используй только предоставленные источники. Не добавляй собственные ссылки, даже если они кажутся релевантными.\n"
            "Если источник не подходит по смыслу, не используй его.\n"
            "Если ты не знаешь ответа — так и скажи. Если вопрос не юридический — сообщи об этом прямо.\n"
            "Отвечай просто текстом. Не используй жирный, курсив, заголовки или иное форматирование Markdown.\n"
            "Ниже приведены тексты законов и судебных решений. Они всегда заключены в квадратрые скобки [].\n\n"
            "Потенциально подходящие законы:\n" + "\n".join(law_texts) + "\n\n"
            "Потенциально подходящие судебные решения:\n" + "\n".join(case_texts)
        ),
    }


def build_system_prompt_zero():
    return {
        "role": "system",
        "content": (
            "Ты виртуальный ассистент-юрист для пользователей из Российской Федерации. "
            "Твоя задача — давать точные и обоснованные юридические ответы строго на русском языке.\n"
            "Если ты уверен в ссылке на статью закона или кодекса — можешь её указать. "
            "Но не выдумывай ссылки и не указывай несуществующие источники. "
            "Если не уверен — лучше не ссылайся вовсе.\n"
            "Если не знаешь ответа — прямо скажи об этом. "
            "Если вопрос не связан с юридической помощью — сообщи, что не можешь ответить.\n"
            "Отвечай просто текстом. Не используй жирный, курсив, заголовки или иное форматирование Markdown."
        ),
    }


def log_preview(label, text, max_chars=200):
    if len(text) > max_chars:
        logger.info(f"{label} (truncated): {text[:max_chars]}... [+{len(text) - max_chars} chars]")
    else:
        logger.info(f"{label}: {text}")

async def query_llm(messages, max_retries=5, retry_delay=2):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "top_p": 1,
        "temperature": 0.0,
        "frequency_penalty": 0.2,            
        "presence_penalty": 0,               
        "repetition_penalty": 1.05,
        "top_k": 0,
    }

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(LLM_API_URL, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"LLM request failed with status {resp.status}")
                        await asyncio.sleep(retry_delay)
                        continue

                    result = await resp.json()
                    content = (
                        result.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if not content.strip() or "Техническая ошибка" in content:
                        logger.warning(f"Empty or error content (attempt {attempt + 1})")
                        await asyncio.sleep(retry_delay)
                        continue

                    return content.strip()

        except Exception as e:
            logger.warning(f"Exception during LLM query (attempt {attempt + 1})")
            logger.exception(e)
            await asyncio.sleep(retry_delay)

    return "Ответ не получен."


async def run_eval(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Resume support
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f_out:
            results = json.load(f_out)
    else:
        results = []

    answered_map = {entry["question"]: entry for entry in results}

    embedder, reranker, client = load_models()

    for idx, sample in enumerate(dataset):
        question = sample.get("question", "").strip()
        reference = sample.get("answer", "").strip()

        if not question:
            logger.warning(f"Skipping empty question at index {idx}")
            continue

        existing = answered_map.get(question)

        if existing:
            if all(existing.get(k, "").strip() not in ["", "Ответ не получен.", "ERROR"]
                   for k in ["zero_shot", "rag"]):
                logger.info(f"Skipping already completed: {question[:60]}")
                continue
        else:
            existing = {"question": question, "reference": reference}

        logger.info(f"[{idx + 1}/{len(dataset)}] Processing: {question[:60]}")

        try:
            if existing.get("zero_shot", "").strip() in ["", "Ответ не получен.", "ERROR"]:
                zero_prompt = [build_system_prompt_zero(), {"role": "user", "content": question}]
                existing["zero_shot"] = await query_llm(zero_prompt)
                log_preview("Zero-shot response", existing["zero_shot"])

            if existing.get("rag", "").strip() in ["", "Ответ не получен.", "ERROR"]:
                law_docs = await get_reranked_law_articles(
                    query=question,
                    embedder=embedder,
                    reranker=reranker,
                    client=client,
                    inference_backend=INFERENCE_BACKEND,
                    remote_reranker_model="BAAI/bge-reranker-v2-m3",
                )
                case_docs = await get_reranked_case_chunks(
                    query=question,
                    embedder=embedder,
                    reranker=reranker,
                    client=client,
                    inference_backend=INFERENCE_BACKEND,
                    remote_reranker_model="BAAI/bge-reranker-v2-m3",
                )

                law_texts = [doc["text"] for doc in law_docs]
                case_texts = [doc["text"] for doc in case_docs]

                prompt_content = build_system_prompt_rag(law_texts, case_texts)["content"]
                if len(prompt_content) > 150000:
                    logger.warning(f"⚠️ RAG prompt very large: {len(prompt_content)} characters")

                rag_prompt = [
                    build_system_prompt_rag(law_texts, case_texts),
                    {"role": "user", "content": question},
                ]
                existing["rag"] = await query_llm(rag_prompt)
                log_preview("RAG response", existing["rag"])

            # Update result map
            answered_map[question] = existing

        except Exception as e:
            logger.exception(f"Error on question {idx + 1}: {question}")
            existing["zero_shot"] = existing.get("zero_shot", "ERROR")
            existing["rag"] = existing.get("rag", "ERROR")

        results = list(answered_map.values())

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as save_err:
            logger.error(f"Failed to save results: {save_err}")

    logger.info(f"✅ Finished. Final results saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(run_eval("generation_eval_dset.json", "generation_eval_results.json"))
