import onnxruntime
from transformers import AutoTokenizer
import numpy as np

class ONNXReranker:
    def __init__(self, model_path, tokenizer_name="BAAI/bge-reranker-v2-m3"):
        self.session = onnxruntime.InferenceSession(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

    def predict(self, pairs):
        inputs = self.tokenizer(
            [q for q, d in pairs],
            [d for q, d in pairs],
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=8192
        )
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }
        logits = self.session.run(None, onnx_inputs)[0]
        return logits.squeeze().tolist()
