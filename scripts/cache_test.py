"""Problem 4: run all 12 practice docs with prompt caching, then without, and save output/cache_test.json.

Run from the repo root:  python scripts/cache_test.py
MODEL: gpt-6-luna (agent.py). A no_cache run only counts if the API reports 0 cached tokens.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: agent.py, tools.py, models.py

import json
from datetime import datetime

import agent

HW6_DIR = Path(__file__).resolve().parent.parent
DOCS = sorted((HW6_DIR / "data" / "practice_docs").iterdir())
KEY = {k["file"]: k for k in json.loads((HW6_DIR / "data" / "practice_key.json").read_text(encoding="utf-8"))}
OUT = HW6_DIR / "output" / "cache_test.json"
FIELDS = ["vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision"]


def main() -> None:
    agent.ensure_trap_log()
    prices = json.loads(agent.PRICES_FILE.read_text(encoding="utf-8"))[agent.MODEL_NAME]
    runs = []
    for setup, cache in (("cached", True), ("no_cache", False)):
        for doc in DOCS:
            answer, log, per_request = agent.review(doc, cache=cache)
            key = KEY[doc.name]
            wrong = [f for f in FIELDS if getattr(answer, f) != key[f]]
            valid = cache or log.cached_input_tokens == 0
            runs.append({
                "setup": setup,
                "doc": doc.name,
                "valid": valid,
                **log.model_dump(exclude={"document", "setup"}),
                "per_request": per_request,
                "decision": answer.decision,
                "matches_key": not wrong,
                "wrong_fields": wrong,
            })
            print(f"{setup:8} {doc.name:28} in={log.input_tokens:6} cached={log.cached_input_tokens:6} "
                  f"write={log.cache_write_tokens:4} out={log.output_tokens:4} ${log.cost_usd:.6f} "
                  f"{'OK' if not wrong else 'WRONG ' + ','.join(wrong)}{'' if valid else '  INVALID (cached tokens)'}")

    summary = {}
    for setup in ("cached", "no_cache"):
        rows = [r for r in runs if r["setup"] == setup]
        summary[setup] = {
            "docs": len(rows),
            "all_valid": all(r["valid"] for r in rows),
            **{k: sum(r[k] for r in rows) for k in
               ("requests", "input_tokens", "cached_input_tokens", "cache_write_tokens",
                "output_tokens", "reasoning_tokens", "cost_usd")},
            "matches_key": sum(r["matches_key"] for r in rows),
        }
        summary[setup]["cost_usd"] = round(summary[setup]["cost_usd"], 8)
        summary[setup]["cost_per_doc_usd"] = round(summary[setup]["cost_usd"] / len(rows), 8)

    OUT.write_text(json.dumps({
        "created": datetime.now().isoformat(timespec="seconds"),
        "model": agent.MODEL_NAME,
        "reasoning_effort": agent.REASONING_EFFORT,
        "prices_per_1m_usd": prices,
        "setups": {
            "cached": "Prompt + handbook sent as an identical prefix on every request, with a prompt_cache_key.",
            "no_cache": "A random id is placed at the start of the instructions on every request, so no two "
                        "requests share a prefix and OpenAI cannot read from its prompt cache.",
        },
        "cost_formula": "((input - cached - cache_write) * input_per_1m + cached * cached_input_per_1m"
                        " + cache_write * cache_write_per_1m + output * output_per_1m) / 1,000,000",
        "summary": summary,
        "runs": runs,
    }, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
