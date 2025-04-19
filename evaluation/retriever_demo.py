import os
import argparse
from huggingface_hub import login
from dotenv import load_dotenv
from retrieval import (
    load_model,
    get_qdrant_client,
    search_qdrant,
    load_config,
)
from logger import get_logger


def main(config_name):
    config = load_config(config_name)
    logger.info(f"Using config: {config_name}")
    model_name = config["embedding_model"]
    logger.info(f"Using model: {model_name}")
    model = load_model(model_name)
    client = get_qdrant_client()

    collection_name = config["collection_name"]
    top_k = config.get("retriever", {}).get("top_k", 5)

    logger.info(f"Using Qdrant collection: {collection_name}")
    print("Type your legal query (or 'exit' to quit):")

    while True:
        query = input("\nQuery: ").strip()
        if query.lower() in ["exit", "quit"]:
            logger.info("Session ended by user.")
            break

        try:
            vector = model.encode([query], normalize_embeddings=True)[0]
            results = search_qdrant(
                client, collection_name, vector, top_k=top_k, hnsw_ef=128
            )

            if not results:
                print("No results found.")
                logger.info(f"No results for query: {query}")
                continue

            print(f"\nTop {top_k} results:\n" + "-" * 40)
            for i, hit in enumerate(results, 1):
                payload = hit.payload
                print(f"\n[{i}] score={hit.score:.4f}")
                print(payload.get("text", "[No text]"))
            print("-" * 40)

        except Exception as e:
            logger.exception(f"Failed to process query: {query}")


if __name__ == "__main__":
    load_dotenv()
    login(os.getenv("HF_TOKEN"))
    logger = get_logger()

    parser = argparse.ArgumentParser(
        description="Interactive legal search using Qdrant and SentenceTransformer"
    )
    parser.add_argument(
        "config_name",
        nargs="?",
        default=None,
        help="Name of the config file (without .yaml)",
    )
    args = parser.parse_args()

    if not args.config_name:
        logger.warning(
            "No config name provided. Falling back to default: 'laws_jina_1024'"
        )
        args.config_name = "laws_jina_1024"

    main(args.config_name)
