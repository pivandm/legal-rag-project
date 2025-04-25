from sentence_transformers import SentenceTransformer
from retrieval import ONNXReranker
from retrieval import get_qdrant_client

def load_models():
    embedder = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
    reranker = ONNXReranker()
    client = get_qdrant_client()
    return embedder, reranker, client
