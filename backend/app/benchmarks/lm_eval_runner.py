"""lm-evaluation-harness runner for HellaSwag and MMLU.

Requires: pip install lm-eval
Optional — if not installed, these tasks are skipped gracefully.
"""

from __future__ import annotations


def run_lm_eval(model_id: str, device: str, tasks: list[str], num_fewshot: int = 0) -> dict[str, float]:
    """Run lm-eval tasks and return {task_name: score} dict.

    Returns empty dict if lm-eval is not installed.
    """
    try:
        import lm_eval
        from lm_eval.models.huggingface import HFLM
    except ImportError:
        return {}

    model = HFLM(pretrained=model_id, device=device)
    results = lm_eval.simple_evaluate(
        model=model,
        tasks=tasks,
        num_fewshot=num_fewshot,
        batch_size="auto",
    )

    scores: dict[str, float] = {}
    for task in tasks:
        task_results = results["results"].get(task, {})
        # Prefer acc_norm, fall back to acc
        score = task_results.get("acc_norm,none") or task_results.get("acc,none") or 0.0
        scores[task] = round(float(score), 4)

    return scores
