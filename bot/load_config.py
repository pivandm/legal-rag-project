import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    if "reranker" not in config:
        raise ValueError("Missing 'reranker' section in config.yaml")

    reranker = config["reranker"]
    if reranker["type"] == "onnx_quantized":
        if not reranker.get("model_path"):
            raise ValueError("Expected 'model_path' for ONNX quantized reranker")
    elif reranker["type"] == "normal":
        if not reranker.get("model_name"):
            raise ValueError("Expected 'model_name' for normal reranker")
    else:
        raise ValueError(f"Unsupported reranker type: {reranker['type']}")

    return config
