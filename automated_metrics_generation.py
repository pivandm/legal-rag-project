import json
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer

# Load JSON
with open("generation_eval_results.json", encoding="utf-8") as f:
    data = json.load(f)

# Initialize metrics
smoothie = SmoothingFunction().method4
rouge = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)

bleu_zero_shot, bleu_rag = [], []
rouge_zero_shot, rouge_rag = [], []

for item in data:
    reference = [item["reference"].split()]
    zero_shot = item["zero_shot"].split()
    rag = item["rag"].split()

    # BLEU
    bleu_zero_shot.append(
        sentence_bleu(reference, zero_shot, smoothing_function=smoothie)
    )
    bleu_rag.append(sentence_bleu(reference, rag, smoothing_function=smoothie))

    # ROUGE
    rouge_zero_shot.append(rouge.score(item["reference"], item["zero_shot"]))
    rouge_rag.append(rouge.score(item["reference"], item["rag"]))


# Aggregate results
def avg_bleu(scores):
    return sum(scores) / len(scores)


def avg_rouge(rouge_scores, key):
    return sum([x[key].fmeasure for x in rouge_scores]) / len(rouge_scores)


print("\n--- Zero-Shot ---")
print(f"BLEU: {avg_bleu(bleu_zero_shot):.4f}")
print(f"ROUGE-1: {avg_rouge(rouge_zero_shot, 'rouge1'):.4f}")
print(f"ROUGE-L: {avg_rouge(rouge_zero_shot, 'rougeL'):.4f}")

print("\n--- RAG ---")
print(f"BLEU: {avg_bleu(bleu_rag):.4f}")
print(f"ROUGE-1: {avg_rouge(rouge_rag, 'rouge1'):.4f}")
print(f"ROUGE-L: {avg_rouge(rouge_rag, 'rougeL'):.4f}")
