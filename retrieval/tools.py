import os
import aiohttp
from dotenv import load_dotenv
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.models import SparseVector, Prefetch, FusionQuery, Fusion
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from logger import auto_logger

# Load environment variables
load_dotenv()
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
HF_TOKEN = os.getenv("HF_TOKEN")


def get_qdrant_client():
    return AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


@auto_logger
def load_dense_model(model_name: str, logger=None):
    logger.info(f"Loading dense model: {model_name}")
    return SentenceTransformer(model_name, trust_remote_code=True)


@auto_logger
def load_sparse_model(model_name="Qdrant/bm25", logger=None):
    logger.info(f"Loading sparse model: {model_name}")
    return SparseTextEmbedding(model_name=model_name)


async def remote_encode_hf(query, model_name, hf_token):
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": query}
    url = (
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            vector = await response.json()
            return [float(sum(col) / len(col)) for col in zip(*vector)]


async def remote_rerank_hf(query, docs, model_name, hf_token, top_k=5):
    headers = {"Authorization": f"Bearer {hf_token}"}
    inputs = [{"query": query, "documents": [doc["text"] for doc in docs]}]
    url = f"https://api-inference.huggingface.co/models/{model_name}"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=inputs) as response:
            response.raise_for_status()
            scores = await response.json()
            if isinstance(scores, list) and "scores" in scores[0]:
                sorted_indices = sorted(
                    enumerate(scores[0]["scores"]), key=lambda x: x[1], reverse=True
                )
                return [docs[i] for i, _ in sorted_indices[:top_k]]
            return docs[:top_k]


@auto_logger
async def search_qdrant(
    client,
    collection_name: str,
    query_text: str,
    top_k: int = 5,
    retriever_type: str = "dense",
    dense_model=None,
    sparse_model=None,
    logger=None,
):
    if retriever_type not in {"dense", "sparse", "hybrid"}:
        raise ValueError(f"Unknown retriever type: {retriever_type}")

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

    if retriever_type == "dense":
        return await client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
    elif retriever_type == "sparse":
        return await client.query_points(
            collection_name=collection_name,
            query=sparse_vector,
            using="sparse",
            limit=top_k,
            with_payload=True,
        )
    else:
        return await client.query_points(
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
async def search_with_precomputed_vectors(
    client,
    collection_name: str,
    top_k: int = 5,
    retriever_type: str = "dense",
    dense_vector=None,
    sparse_vector=None,
    logger=None,
):
    if retriever_type == "dense":
        if dense_vector is None:
            raise ValueError("Dense vector must be provided for dense retrieval")
        return await client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            using="dense",
            limit=top_k,
            with_payload=True,
        )
    elif retriever_type == "sparse":
        if sparse_vector is None:
            raise ValueError("Sparse vector must be provided for sparse retrieval")
        return await client.query_points(
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
        return await client.query_points(
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
        docs.append({"text": text, "url": url})
    return docs


@auto_logger
async def get_reranked_law_articles(
    query,
    embedder,
    reranker,
    client,
    inference_backend="local",
    remote_reranker_model=None,
    logger=None,
):
    res = await search_qdrant(
        client=client,
        collection_name="bge-laws-2048-chunks",
        query_text=query,
        top_k=10,
        retriever_type="dense",
        dense_model=embedder,
    )
    docs = prepare_laws_from_qdrant(res.points)

    if inference_backend == "remote":
        reranked = await remote_rerank_hf(
            query, docs, remote_reranker_model, HF_TOKEN, top_k=5
        )
    else:
        reranked = reranker.predict([(query, doc["text"]) for doc in docs])
        reranked = [
            doc
            for doc, _ in sorted(zip(docs, reranked), key=lambda x: x[1], reverse=True)
        ][:5]

    for doc in reranked:
        if "url" in doc:
            doc["text"] = f"[Ссылка на закон]({doc['url']})\nНазвание и текст источника: {doc['text']}"
    return reranked


@auto_logger
async def get_reranked_case_chunks(
    query,
    embedder,
    reranker,
    client,
    inference_backend="local",
    remote_reranker_model=None,
    logger=None,
):
    res = await search_qdrant(
        client=client,
        collection_name="bge-cases-2048-chunks",
        query_text=query,
        top_k=5,
        retriever_type="dense",
        dense_model=embedder        
    )

    raw_chunks = []
    for r in res.points:
        payload = r.payload or {}
        meta = payload.get("metadata", {}).get("metadata", {})
        case_no = meta.get("case_no")
        if not case_no:
            continue

        raw_chunks.append(
            {
                "text": payload.get("text", ""),
                "case_no": case_no,
                "case_url": meta.get("case_url"),
                "operative": meta.get("operative", ""),
            }
        )

    if inference_backend == "remote":
        reranked_chunks = await remote_rerank_hf(
            query, raw_chunks, remote_reranker_model, HF_TOKEN, top_k=5
        )
    else:
        scores = reranker.predict([(query, doc["text"]) for doc in raw_chunks])
        reranked_chunks = [
            doc
            for doc, _ in sorted(
                zip(raw_chunks, scores), key=lambda x: x[1], reverse=True
            )
        ][:5]

    grouped = {}
    for chunk in reranked_chunks:
        case_no = chunk["case_no"]
        if case_no not in grouped:
            grouped[case_no] = {
                "case_no": case_no,
                "case_url": chunk["case_url"],
                "operative": chunk.get("operative", ""),
                "chunks": [],
            }
        grouped[case_no]["chunks"].append(chunk["text"])

    final_docs = []
    for case in grouped.values():
        full_text = "\n".join(case["chunks"])
        full_text = f"[Ссылка на судебное решение]({case['case_url']})\nЧасть фабулы:{full_text.strip()}\nРезолютивная часть:{case['operative']}"
        final_docs.append(
            {
                "text": full_text,
                "case_url": case["case_url"],
                "case_no": case["case_no"],
            }
        )

    return final_docs[:2]
