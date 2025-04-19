import sys
import json
from dotenv import load_dotenv
from logger import get_logger
from retrieval.config import load_config
from retrieval.tools import (
    load_model,
    get_qdrant_client,
    search_qdrant,
    match_article,
)

load_dotenv()
logger = get_logger()


def load_eval_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(retrieved, relevant, k):
    top_k = retrieved[:k]
    correct = [pred for pred in top_k if any(match_article(pred, g) for g in relevant)]
    precision_at_k = len(correct) / k

    hits = 0
    ap = 0.0
    for i, pred in enumerate(top_k):
        if any(match_article(pred, g) for g in relevant):
            hits += 1
            ap += hits / (i + 1)
    map_at_k = ap / len(relevant) if relevant else 0.0

    rr = 0.0
    for i, pred in enumerate(retrieved):
        if any(match_article(pred, g) for g in relevant):
            rr = 1 / (i + 1)
            break

    return precision_at_k, map_at_k, rr


def run_retriever_eval(config_name, eval_data_path):
    config = load_config(config_name)
    model = load_model(config["embedding_model"])
    client = get_qdrant_client()
    collection = config["collection_name"]
    kwargs = config.get("model_kwargs", {})
    top_k = config.get("retriever", {}).get("top_k", 5)
    logger.info(f"Evaluating retriever with config: {config_name}")
    logger.info(
        f"Collection: {collection}, Model: {config['embedding_model']}, top_k: {top_k}"
    )

    eval_data = load_eval_data(eval_data_path)

    p_at_k_scores = []
    map_at_k_scores = []
    mrr_scores = []
    hit_at_k_counts = {1: 0, 3: 0, 5: 0}
    missed_queries = []

    for sample in eval_data:
        query = sample["query"]
        relevant_articles = sample["relevant_articles"]

        try:
            vector = model.encode([query], normalize_embeddings=True, **kwargs)[0]

            results = search_qdrant(
                client=client,
                collection=collection,
                query_vector=vector,
                top_k=top_k,
                hnsw_ef=256,  # use higher ef for eval
            )

            retrieved = [
                {
                    "law_code": res.payload.get("law_code"),
                    "law_number": res.payload.get("law_number"),
                }
                for res in results
            ]

            p, ap, rr = compute_metrics(retrieved, relevant_articles, top_k)
            p_at_k_scores.append(p)
            map_at_k_scores.append(ap)
            mrr_scores.append(rr)

            for i, pred in enumerate(retrieved):
                if any(match_article(pred, g) for g in relevant_articles):
                    for k in hit_at_k_counts:
                        if i < k:
                            hit_at_k_counts[k] += 1
                    break
            else:
                missed_queries.append(query)

        except Exception as e:
            logger.exception(f"Error processing query: {query}")
            missed_queries.append(query)

    total = len(eval_data)
    logger.info(f"Evaluation Results on {total} queries:")
    logger.info(f"Mean P@{top_k}: {sum(p_at_k_scores) / total:.3f}")
    logger.info(f"MAP@{top_k}: {sum(map_at_k_scores) / total:.3f}")
    logger.info(f"MRR: {sum(mrr_scores) / total:.3f}")
    for k in sorted(hit_at_k_counts):
        logger.info(f"Hit@{k}: {hit_at_k_counts[k] / total:.3f}")

    if missed_queries:
        logger.info(f"Missed {len(missed_queries)} queries:")
        for q in missed_queries:
            logger.info(f"- {q}")


if __name__ == "__main__":
    config_name = sys.argv[1] if len(sys.argv) > 1 else "laws_jina_1024"
    eval_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "evaluation\eval_queries_koap_realistic.json"
    )

    run_retriever_eval(config_name, eval_path)
    logger.info("Retriever evaluation completed.")
