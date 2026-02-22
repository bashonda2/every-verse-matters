import json
from pathlib import Path
from datetime import datetime

# Approximate pricing per 1M tokens (as of early 2026)
PRICING = {
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
}


def estimate_cost(usage: dict) -> float:
    model = usage.get("model", "claude-opus-4-6")
    prices = PRICING.get(model, PRICING["claude-opus-4-6"])
    input_cost = (usage["input_tokens"] / 1_000_000) * prices["input"]
    output_cost = (usage["output_tokens"] / 1_000_000) * prices["output"]
    return round(input_cost + output_cost, 4)


def log_pipeline_run(
    week: int,
    year: int,
    stage: str,
    usage_list,
    status="success",
    errors=None,
    output_path=None,
):
    log_path = Path(__file__).parent.parent.parent / "logs" / "pipeline_runs.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    total_input = sum(u["input_tokens"] for u in usage_list)
    total_output = sum(u["output_tokens"] for u in usage_list)
    total_cost = sum(estimate_cost(u) for u in usage_list)
    total_elapsed = sum(u.get("elapsed_seconds", 0) for u in usage_list)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "week": week,
        "year": year,
        "stage": stage,
        "status": status,
        "api_calls": len(usage_list),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "estimated_cost_usd": total_cost,
        "total_elapsed_seconds": round(total_elapsed, 2),
        "errors": errors or [],
        "output_path": output_path,
    }

    runs = []
    if log_path.exists():
        with open(log_path) as f:
            runs = json.load(f)

    runs.append(entry)

    with open(log_path, "w") as f:
        json.dump(runs, f, indent=2)

    return entry
