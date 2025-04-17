import os
import uuid
import json
import logging
import numpy as np
import argparse
import time
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from retrieval import load_config
from logger import get_logger

logger = get_logger()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))


def main(config):
    start_time = time.time()
    try:
        collection_name = config["collection_name"]
        vector_file = config["vectors_path"]
        metadata_file = config["metadata_path"]
        vector_size = config["chunking"]["max_tokens"]

        logger.info(f"Using config for collection: {collection_name}")
        logger.info(f"Vector file: {vector_file}")
        logger.info(f"Metadata file: {metadata_file}")
        logger.info(f"Vector size: {vector_size}")

        # Load vectors and metadata
        logger.info("Loading vectors and metadata...")
        vectors = np.load(vector_file)
        with open(metadata_file, "r", encoding="utf-8") as f:
            payloads = json.load(f)

        assert len(vectors) == len(
            payloads
        ), f"Mismatch between vectors - {len(vectors)} and payloads {len(payloads)}"
        logger.info(f"Loaded {len(vectors)} vectors and {len(payloads)} payloads.")

        # Connect to Qdrant
        logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Recreate collection
        if client.collection_exists(collection_name):
            logger.info(f"Collection '{collection_name}' exists. Deleting...")
            client.delete_collection(collection_name)

        logger.info(f"Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

        # Upload vectors
        logger.info("Uploading points to Qdrant...")
        batch_size = 256
        for i in range(0, len(vectors), batch_size):
            batch_vectors = vectors[i : i + batch_size]
            batch_payloads = payloads[i : i + batch_size]
            batch_ids = [str(uuid.uuid4()) for _ in batch_vectors]

            batch_points = [
                PointStruct(id=pid, vector=vec.tolist(), payload=pl)
                for pid, vec, pl in zip(batch_ids, batch_vectors, batch_payloads)
            ]

            client.upsert(collection_name=collection_name, points=batch_points)
            logger.info(f"Uploaded batch {i}–{i+len(batch_vectors)-1}")

        logger.info(
            f"Upload complete: {len(vectors)} vectors stored in '{collection_name}'."
        )
        elapsed = time.time() - start_time
        logger.info(f"Total time: {elapsed:.2f} seconds")

    except Exception as e:
        logger.exception("Something went wrong during vector upload.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load vectors into Qdrant from config."
    )
    parser.add_argument(
        "config_name", type=str, help="Name of the config file (without .yaml)"
    )
    args = parser.parse_args()

    logger.info(f"Script started with config: {args.config_name}")

    config = load_config(args.config_name)
    main(config)
