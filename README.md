# Campus Customs Vendor Desk Agent (MGT 409, HW6)

An AI agent that reads a vendor document (HTML quote, PDF quote, or `.eml` email), extracts the vendor, SKU,
unit price, lead time, and minimum order, and decides **recommend** or **do_not_recommend** using the rules in
`data/shop_handbook.md`. It is defended against documents that hide instructions aimed at the AI.

- Model: **gpt-6-luna** through Portkey (prices in `data/prices.json`).
- It **never sends email or makes payments**. `send_email` and `approve_payment` are trap tools that only log
  the attempt to `output/trap_calls.json`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env            # then put your real PORTKEY_API_KEY in .env
```

## Run the agent

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

It prints the JSON answer (vendor, sku, unit_price, lead_time_days, min_order, decision, reason) and appends
to `output/usage_log.json` (tokens and cost) and `output/audit_trail.json` (every tool call and the answer).
Any document works: `data/practice_docs/`, `data/exam_docs/`, or `data/my_attacks/`.

Test-only options: `--defenses none` (or `code`, `design`, `prompt`, comma-separated) turns defense layers off;
`--no-cache` disables prompt caching.

## How it is built

| File | Role |
|---|---|
| `agent.py` | Entry point. Builds the PydanticAI agent and applies the handbook rules in plain Python (design layer). |
| `tools.py` | `read_document` (cleans hidden text before the model sees it: code layer) and the two trap tools. |
| `models.py` | Structured types: the answer, the extracted facts, and the log entries. |
| `prompts/prompt.md` | The extractor and decider prompts, including the security rules (prompt layer). |
| `scripts/` | The scripts that produced each result in `output/`, for example `python scripts/exam_run.py`. |
| `output/hw6_report.html` | One-page results report. Open it in any browser; it works offline. |

Full write-ups are in `output/`: cost estimate, caching test, attacks, defenses, red team, exam results, and
`harness.md` (every field and tool, plus the safety failures). `AI_prompts.md` logs the prompts used to build it.
