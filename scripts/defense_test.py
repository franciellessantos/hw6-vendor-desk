"""Problem 6: rerun the 12 practice docs with each defense layer alone and with all three together.

Run from the repo root:  python scripts/defense_test.py
"Before" is the no-defense run saved by attack_test.py (Problem 5) in output/attack_results.json.
MODEL: gpt-6-luna (agent.py). Writes output/defense_results.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: agent.py, tools.py, models.py

import json
from datetime import datetime

import agent
from attack_test import OUT as ATTACK_RESULTS, PRACTICE_DIR, PRACTICE_KEY, load_key, run_suite
from models import Defenses

OUT = Path(__file__).resolve().parent.parent / "output" / "defense_results.json"
SETUPS = {
    "code_only": Defenses(code=True, design=False, prompt=False),
    "design_only": Defenses(code=False, design=True, prompt=False),
    "prompt_only": Defenses(code=False, design=False, prompt=True),
    "all_layers": Defenses(code=True, design=True, prompt=True),
}


def main() -> None:
    docs, key = sorted(PRACTICE_DIR.iterdir()), load_key(PRACTICE_KEY)
    before = json.loads(ATTACK_RESULTS.read_text(encoding="utf-8"))["runs"]["no_defenses"]
    runs = {"no_defenses": {"note": "Before: Problem 5 no-defense run.", **before}}
    for name, defenses in SETUPS.items():
        results, summary = run_suite(docs, key, defenses)
        runs[name] = {"summary": summary, "results": results}
        OUT.write_text(json.dumps({"created": datetime.now().isoformat(timespec="seconds"),
                                   "model": agent.MODEL_NAME, "runs": runs}, indent=2), encoding="utf-8")
    for name, run in runs.items():
        print(name, json.dumps(run["summary"]))


if __name__ == "__main__":
    main()
