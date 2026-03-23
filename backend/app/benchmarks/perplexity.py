"""Perplexity benchmark on WikiText-2.

Computes perplexity using a sliding window approach over the test split.
Lower perplexity = better model.
"""

import math

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

# Number of tokens to evaluate (subset for speed — full test set is ~250k tokens)
MAX_TOKENS = 4096
STRIDE = 512


def compute_perplexity(model: AutoModelForCausalLM, tokenizer: AutoTokenizer, device: str) -> float:
    dataset = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    text = "\n\n".join(dataset["text"])  # type: ignore[index]

    encodings = tokenizer(text, return_tensors="pt")
    input_ids = encodings.input_ids[:, :MAX_TOKENS].to(device)
    seq_len = input_ids.size(1)

    nlls = []
    prev_end = 0

    for begin in range(0, seq_len, STRIDE):
        end = min(begin + tokenizer.model_max_length, seq_len)
        target_len = end - prev_end
        chunk = input_ids[:, begin:end]

        # Mask prefix tokens that overlap with previous window
        labels = chunk.clone()
        labels[:, :-target_len] = -100

        with torch.no_grad():
            loss = model(chunk, labels=labels).loss

        nlls.append(loss.item() * target_len)
        prev_end = end

        if end == seq_len:
            break

    perplexity = math.exp(sum(nlls) / seq_len)
    return round(perplexity, 4)
