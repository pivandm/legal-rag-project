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


@auto_logger
def search_qdrant(client, collection: str, query_vector, top_k: int = 5, hnsw_ef: int = 128, logger=None):
    logger.info(f"Searching collection '{collection}' (top_k={top_k}, hnsw_ef={hnsw_ef})")
    return client.search(
        collection_name=collection,
        query_vector=query_vector,
        limit=top_k,
        search_params=SearchParams(hnsw_ef=hnsw_ef),
        with_payload=True,
    )


def match_article(pred, gold):
    return (
        pred.get("law_code") == gold.get("law_code") and
        pred.get("law_number") == gold.get("law_number")
    )
