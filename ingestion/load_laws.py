import os
import uuid
import json
import time
import numpy as np
import argparse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    SparseVector,
    PointStruct,
    Distance,
    SparseIndexParams,
)
from fastembed import SparseTextEmbedding
from retrieval import load_config
from logger import get_logger

logger = get_logger()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))


def main(config):
    start_time = time.time()
    try:
        # Load config
        collection_name = config["collection_name"]
        vector_file = config["vectors_path"]
        metadata_file = config["metadata_path"]
        vector_size = config["vector_dim"]

        logger.info(f"Loading collection config: {collection_name}")
        dense_vectors = np.load(vector_file)
        with open(metadata_file, "r", encoding="utf-8") as f:
            flat_payloads = json.load(f)

        assert len(dense_vectors) == len(
            flat_payloads
        ), "Mismatch between vectors and payloads"

        # Connect to Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Recreate collection
        if client.collection_exists(collection_name):
            logger.info(f"Deleting existing collection '{collection_name}'")
            client.delete_collection(collection_name)

        logger.info(f"Creating hybrid collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=vector_size, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
            },
        )

        # client.create_payload_index(
        #     collection_name=collection_name, field_name="text", field_schema="text"
        # )

        # Sparse encoder
        logger.info("Initializing sparse embedder (BM25)...")
        sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        texts = [p["text"] for p in flat_payloads]
        sparse_vectors = list(sparse_model.embed(texts))

        # Upload points
        logger.info("Uploading vectors...")
        batch_size = 256
        for i in range(0, len(dense_vectors), batch_size):
            batch_dense = dense_vectors[i : i + batch_size]
            batch_sparse = sparse_vectors[i : i + batch_size]
            batch_payloads = flat_payloads[i : i + batch_size]
            batch_ids = [str(uuid.uuid4()) for _ in range(len(batch_dense))]

            points = []
            for pid, vec, sparse_vec, flat_payload in zip(
                batch_ids, batch_dense, batch_sparse, batch_payloads
            ):
                wrapped_payload = {
                    "text": flat_payload["text"],
                    "metadata": {k: v for k, v in flat_payload.items() if k != "text"},
                }

                points.append(
                    PointStruct(
                        id=pid,
                        vector={
                            "dense": vec.tolist(),
                            "sparse": SparseVector(
                                indices=sparse_vec.indices.tolist(),
                                values=sparse_vec.values.tolist(),
                            ),
                        },
                        payload=wrapped_payload,
                    )
                )

            client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Uploaded batch {i}-{i + len(points) - 1}")

        elapsed = time.time() - start_time
        logger.info(f"Upload complete: {len(dense_vectors)} vectors stored.")
        logger.info(f"Total time: {elapsed:.2f} seconds")

    except Exception as e:
        logger.exception("Something went wrong during vector upload.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load hybrid vectors into Qdrant.")
    parser.add_argument(
        "config_name", type=str, help="Name of the config file (without .yaml)"
    )
    args = parser.parse_args()

    logger.info(f"Script started with config: {args.config_name}")
    config = load_config(args.config_name)
    main(config)
