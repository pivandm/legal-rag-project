import os
from qdrant_client import QdrantClient
from qdrant_client.models import SearchParams
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from logger import auto_logger

# Load .env
load_dotenv()
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))


@auto_logger
def load_model(model_name: str, logger=None):
    logger.info(f"Loading model: {model_name}")
    return SentenceTransformer(model_name, trust_remote_code=True)


def get_qdrant_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


from qdrant_client.models import SearchParams


@auto_logger
def search_qdrant(
    client,
    collection: str,
    query_vector=None,
    query_text=None,
    retriever_type="dense",  # options: dense, hybrid, sparse
    top_k: int = 5,
    hnsw_ef: int = 128,
    logger=None,
):
    logger.info(
        f"Searching collection '{collection}' using '{retriever_type}' retriever (top_k={top_k}, hnsw_ef={hnsw_ef})"
    )

    if retriever_type == "dense":
        if query_vector is None:
            raise ValueError("Dense retrieval requires 'query_vector'")
        results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=hnsw_ef),
            with_payload=True,
        )

    elif retriever_type == "hybrid":
        if query_vector is None or query_text is None:
            raise ValueError(
                "Hybrid retrieval requires both 'query_vector' and 'query_text'"
            )
        results = client.search(
            collection_name=collection,
            query=query_text,
            query_vector=query_vector,
            limit=top_k,
            search_params=SearchParams(hnsw_ef=hnsw_ef),
            with_payload=True,
        )

    elif retriever_type == "sparse":
        if query_text is None:
            raise ValueError("Sparse retrieval requires 'query_text'")
        results = client.search(
            collection_name=collection, query=query_text, limit=top_k, with_payload=True
        )

    else:
        raise ValueError(f"Unknown retriever type: {retriever_type}")

    # Log retrieved items and their scores
    for i, res in enumerate(results):
        logger.info(f"Result {i+1}: score={res.score:.4f}, payload={res.payload}")

    return results


def match_article(pred, gold):
    return pred.get("law_code") == gold.get("law_code") and pred.get(
        "law_number"
    ) == gold.get("law_number")
