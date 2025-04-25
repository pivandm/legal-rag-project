import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from logger import auto_logger

# Load environment variables
load_dotenv()
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))


def get_qdrant_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


@auto_logger
def load_dense_model(model_name: str, logger=None):
    logger.info(f"Loading dense model: {model_name}")
    return SentenceTransformer(model_name, trust_remote_code=True)


@auto_logger
def load_sparse_model(model_name="Qdrant/bm25", logger=None):
    logger.info(f"Loading sparse model: {model_name}")
    return SparseTextEmbedding(model_name=model_name)


@auto_logger
def search_qdrant(
    client,
    collection_name: str,
    query_text: str,
    top_k: int = 5,
    retriever_type: str = "dense",  # "dense", "sparse", "hybrid"
    dense_model=None,
    sparse_model=None,
    logger=None,
):
    if retriever_type not in {"dense", "sparse", "hybrid"}:
        raise ValueError(f"Unknown retriever type: {retriever_type}")

    # Compute embeddings
    dense_vector = None
    sparse_vector = None

    if retriever_type in {"dense", "hybrid"}:
        if dense_model is None:
            raise ValueError("Dense model is required for dense or hybrid search.")
        dense_vector = dense_model.encode(query_text, normalize_embeddings=True)

    if retriever_type in {"sparse", "hybrid"}:
        if sparse_model is None:
            raise ValueError("Sparse model is required for sparse or hybrid search.")
        sparse_embed = list(sparse_model.embed([query_text]))[0]
        sparse_vector = SparseVector(
            indices=sparse_embed.indices, values=sparse_embed.values
        )

    # Perform query
    if retriever_type == "dense":
        return client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
    elif retriever_type == "sparse":
        return client.query_points(
            collection_name=collection_name,
            query=sparse_vector,
            using="sparse",
            limit=top_k,
            with_payload=True,
        )
    else:  # hybrid
        return client.query_points(
            collection_name=collection_name,
            query=FusionQuery(fusion=Fusion.RRF),
            prefetch=[
                Prefetch(query=dense_vector, using="dense", limit=20),
                Prefetch(query=sparse_vector, using="sparse", limit=20),
            ],
            limit=top_k,
            with_payload=True,
        )


@auto_logger
def search_with_precomputed_vectors(
    client,
    collection_name: str,
    top_k: int = 5,
    retriever_type: str = "dense",  # "dense", "sparse", "hybrid"
    dense_vector=None,
    sparse_vector=None,
    logger=None,
):
    if retriever_type == "dense":
        if dense_vector is None:
            raise ValueError("Dense vector must be provided for dense retrieval")
        return client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
    elif retriever_type == "sparse":
        if sparse_vector is None:
            raise ValueError("Sparse vector must be provided for sparse retrieval")
        return client.query_points(
            collection_name=collection_name,
            query=sparse_vector,
            using="sparse",
            limit=top_k,
            with_payload=True,
        )
    elif retriever_type == "hybrid":
        if dense_vector is None or sparse_vector is None:
            raise ValueError(
                "Both dense and sparse vectors are required for hybrid retrieval"
            )
        return client.query_points(
            collection_name=collection_name,
            query=FusionQuery(fusion=Fusion.RRF),
            prefetch=[
                Prefetch(query=dense_vector, using="dense", limit=20),
                Prefetch(query=sparse_vector, using="sparse", limit=20),
            ],
            limit=top_k,
            with_payload=True,
        )
    else:
        raise ValueError(f"Invalid retriever type: {retriever_type}")


def match_article(pred, gold):
    return pred.get("law_code") == gold.get("law_code") and pred.get(
        "law_number"
    ) == gold.get("law_number")


def prepare_laws_from_qdrant(points):
    docs = []
    for r in points:
        payload = r.payload or {}
        meta = payload.get("metadata", {})
        url = meta.get("url")
        text = payload.get("text", "")
        docs.append({
            "text": text,
            "url": url
        })
    return docs


@auto_logger
def rerank_results(query_text, retrieved_docs, reranker, top_k=5, logger=None):
    if not retrieved_docs:
        logger.warning(f"No docs to rerank for query: {query_text}")
        return []

    try:
        pairs = [(query_text, doc["text"]) for doc in retrieved_docs]
        scores = reranker.predict(pairs)
        reranked = [doc for doc, _ in sorted(zip(retrieved_docs, scores), key=lambda x: x[1], reverse=True)]
        return reranked[:top_k]
    except Exception as e:
        logger.error(f"Reranking failed for query: {query_text}\n{e}")
        return retrieved_docs[:top_k]

def get_reranked_law_articles(query, embedder, reranker, client):
    res = search_qdrant(
        client=client,
        collection_name="bge-laws-2048-chunks",
        query_text=query,
        top_k=10,
        retriever_type="dense",
        dense_model=embedder
    )
    docs = prepare_laws_from_qdrant(res.points)
    reranked = rerank_results(query, docs, reranker, top_k=5)

    # Add URL to beginning of the text
    for doc in reranked:
        if "url" in doc:
            url = doc["url"]
            doc["text"] = f"[Ссылка на закон]({url})\n{doc['text']}"
    return reranked


def get_reranked_case_chunks(query, embedder, reranker, client):
    # Step 1: Initial Qdrant search for top chunks
    res = search_qdrant(
        client=client,
        collection_name="bge-cases-2048-chunks",
        query_text=query,
        top_k=5,
        retriever_type="dense",
        dense_model=embedder
    )

    # Step 2: Extract raw chunks
    raw_chunks = []
    for r in res.points:
        payload = r.payload or {}
        meta = payload.get("metadata", {}).get("metadata", {})
        case_no = meta.get("case_no")
        if not case_no:
            continue

        raw_chunks.append({
            "text": payload.get("text", ""),  # text is still top-level
            "case_no": case_no,
            "case_url": meta.get("case_url"),
            "operative": meta.get("operative", "")
        })

    # Step 3: Rerank chunks
    reranked_chunks = rerank_results(query, raw_chunks, reranker, top_k=5)

    # Step 4: Group reranked chunks by case_no
    grouped = {}
    for chunk in reranked_chunks:
        case_no = chunk["case_no"]
        if case_no not in grouped:
            grouped[case_no] = {
                "case_no": case_no,
                "case_url": chunk["case_url"],
                "operative": chunk.get("operative", ""),
                "chunks": []
            }
        grouped[case_no]["chunks"].append(chunk["text"])

    # Step 5: Combine final docs
    final_docs = []
    for case in grouped.values():
        full_text = "\n".join(case["chunks"])
        full_text = f"[Ссылка на судебное решение]({case['case_url']})\nЧасть фабулы:{full_text.strip()}\Резолютивная часть:{case['operative']}"
        final_docs.append({
            "text": full_text,
            "case_url": case["case_url"],
            "case_no": case["case_no"]
        })

    return final_docs[:2]  # Return top 2 cases
