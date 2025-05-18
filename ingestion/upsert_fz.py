import os
import uuid
import json
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, SparseVectorParams, SparseVector, PointStruct, Distance, SparseIndexParams
from fastembed import SparseTextEmbedding

# Constants
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "bge-laws-2048-chunks"

# Load data
vectors_path = "data/embeddings/vectors_fz.npy"
metadata_path = "data/embeddings/metadata_fz.json"

dense_vectors = np.load(vectors_path)
vector_size = dense_vectors.shape[1]

with open(metadata_path, "r", encoding="utf-8") as f:
    payloads = json.load(f)

assert len(dense_vectors) == len(payloads), "Mismatch between vectors and payloads"

# Connect to Qdrant
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Create collection
if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(COLLECTION_NAME)

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config={"dense": VectorParams(size=vector_size, distance=Distance.COSINE)},
    sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))}
)

# Generate sparse vectors
texts = [p["text"] for p in payloads]
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
sparse_vectors = list(sparse_model.embed(texts))

# Upsert points
batch_size = 256
for i in range(0, len(dense_vectors), batch_size):
    batch_dense = dense_vectors[i:i + batch_size]
    batch_sparse = sparse_vectors[i:i + batch_size]
    batch_payloads = payloads[i:i + batch_size]
    batch_ids = [str(uuid.uuid4()) for _ in range(len(batch_dense))]

    points = []
    for pid, vec, sparse_vec, pl in zip(batch_ids, batch_dense, batch_sparse, batch_payloads):
        wrapped_payload = {
            "text": pl["text"],
            "metadata": {k: v for k, v in pl.items() if k != "text"},
        }
        points.append(PointStruct(
            id=pid,
            vector={
                "dense": vec.tolist(),
                "sparse": SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values=sparse_vec.values.tolist(),
                ),
            },
            payload=wrapped_payload,
        ))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Uploaded batch {i}-{i + len(points) - 1}")
