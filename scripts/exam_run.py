"""Problem 8: run the final defended agent (code + design + prompt) on the 10 exam docs.

Run from the repo root:  python scripts/exam_run.py
MODEL: gpt-6-luna (agent.py). Writes output/exam_results.json, one entry per file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: agent.py, tools.py, models.py

import json

import agent
import tools
from models import Defenses

HW6_DIR = Path(__file__).resolve().parent.parent
EXAM_DIR = HW6_DIR / "data" / "exam_docs"
OUT = HW6_DIR / "output" / "exam_results.json"


def main() -> None:
    agent.ensure_trap_log()
    entries = []
    for doc in sorted(EXAM_DIR.iterdir()):
        answer, log, _ = agent.review(doc, cache=True, defenses=Defenses())
        traps = [t for t in json.loads(tools.TRAP_LOG.read_text(encoding="utf-8")) if t["run_id"] == log.run_id]
        entries.append({
            "file": doc.name,
            **answer.model_dump(),
            "trap_tool_called": bool(traps),
            "input_tokens": log.input_tokens,
            "cached_tokens": log.cached_input_tokens,
            "output_tokens": log.output_tokens,
            "cost_usd": log.cost_usd,
        })
        e = entries[-1]
        print(f"{doc.name:20} {e['vendor']:26} {e['sku']} ${e['unit_price']} {e['lead_time_days']}d "
              f"{e['min_order']}u {e['decision']:17} trap={e['trap_tool_called']} | {e['reason']}", flush=True)
    OUT.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"total ${sum(e['cost_usd'] for e in entries):.6f}")


if __name__ == "__main__":
    main()
