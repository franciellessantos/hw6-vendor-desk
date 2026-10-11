"""Problem 7: run our own attack docs (data/my_attacks/) against the no-defense and the defended agent.

Run from the repo root:  python scripts/make_attacks.py && python scripts/red_team.py
MODEL: gpt-6-luna (agent.py). Each setup runs 3 times, because one lucky run proves little.
Writes output/red_team_results.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root: agent.py, tools.py, models.py

import json
from datetime import datetime

import agent
from attack_test import load_key, run_suite
from models import Defenses

HW6_DIR = Path(__file__).resolve().parent.parent
ATTACK_DIR = HW6_DIR / "data" / "my_attacks"
OUT = HW6_DIR / "output" / "red_team_results.json"
TRIALS = 3
SETUPS = {"no_defenses": Defenses(code=False, design=False, prompt=False), "defended": Defenses()}


def main() -> None:
    docs = sorted(p for p in ATTACK_DIR.iterdir() if p.suffix in (".pdf", ".eml", ".html"))
    key = load_key(ATTACK_DIR / "key.json")
    runs = {}
    for name, defenses in SETUPS.items():
        trials = [run_suite(docs, key, defenses)[0] for _ in range(TRIALS)]
        runs[name] = {doc.name: [t[i] for t in trials] for i, doc in enumerate(docs)}
    OUT.write_text(json.dumps({"created": datetime.now().isoformat(timespec="seconds"),
                               "model": agent.MODEL_NAME, "trials": TRIALS, "runs": runs}, indent=2),
                   encoding="utf-8")
    for name, per_doc in runs.items():
        for doc, rows in per_doc.items():
            print(name, doc, f"fooled {sum(r['fooled'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
