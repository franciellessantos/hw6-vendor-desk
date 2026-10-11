"""Problem 2: size up the handbook and write output/handbook_estimate.md.

Run from the repo root:  python scripts/handbook_estimate.py
MODEL: gpt-6-luna through Portkey, the only model used. Two tiny calls (about $0.001 total)
confirm the offline token count against the model's own usage report.
"""

import json
import os
from pathlib import Path

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

HW6_DIR = Path(__file__).resolve().parent.parent
HANDBOOK = HW6_DIR / "data" / "shop_handbook.md"
PRICES = HW6_DIR / "data" / "prices.json"
OUT = HW6_DIR / "output" / "handbook_estimate.md"

MODEL_NAME = "gpt-6-luna"
ENCODING = "o200k_base"  # tokenizer used by OpenAI's current GPT model family
CALLS = 1000

load_dotenv(HW6_DIR / ".env")
load_dotenv(HW6_DIR.parent / ".env")  # fallback: the course folder .env, when the repo sits inside it


def client() -> OpenAI:
    key = os.environ["PORTKEY_API_KEY"]
    return OpenAI(
        api_key=key,
        base_url="https://api.portkey.ai/v1",
        default_headers={
            "x-portkey-api-key": key,
            "x-portkey-provider": "openai",
            "x-portkey-cache-force-refresh": "true",
        },
    )


def measured_input_tokens(text: str) -> int:
    """Input tokens the model reports for one request (handbook as instructions + a one-word input)."""
    resp = client().responses.create(
        model=MODEL_NAME,
        instructions=text,
        input="ok",
        max_output_tokens=16,
    )
    assert resp.model.startswith(MODEL_NAME), f"unexpected model {resp.model}"
    return resp.usage.input_tokens


def usd(x: float) -> str:
    return f"${x:,.6f}" if x < 0.01 else f"${x:,.4f}"


def main() -> None:
    text = HANDBOOK.read_text(encoding="utf-8")
    p = json.loads(PRICES.read_text(encoding="utf-8"))[MODEL_NAME]

    chars = len(text)
    words = len(text.split())
    tokens = len(tiktoken.get_encoding(ENCODING).encode(text))

    # Model check: the request with the handbook minus the same request with a one-character
    # instruction leaves only the handbook's tokens (the chat-format overhead cancels out).
    with_hb = measured_input_tokens(text)
    without_hb = measured_input_tokens(".")
    measured = with_hb - without_hb + 1  # +1 adds back the "." placeholder token

    t = tokens  # tokenizer count is the official figure; the model check confirms it
    in_rate = p["input_per_1m"] / 1_000_000
    cached_rate = p["cached_input_per_1m"] / 1_000_000
    write_rate = p["cache_write_per_1m"] / 1_000_000

    one_uncached = t * in_rate
    one_write = t * write_rate
    one_cached = t * cached_rate
    k_uncached = CALLS * one_uncached
    k_cached = one_write + (CALLS - 1) * one_cached
    saving = k_uncached - k_cached

    md = f"""# Problem 2 — Handbook size and cost estimate

File measured: `data/shop_handbook.md`
Model: **{MODEL_NAME}** (the only model used)
Prices: `data/prices.json` ({p_source(PRICES)})
Reproduce: `python scripts/handbook_estimate.py` from the repo root

## 1. Token count

| Measure | Value |
|---|---|
| Characters | {chars:,} |
| Words (split on whitespace) | {words:,} |
| **Tokens (tiktoken `{ENCODING}`)** | **{tokens:,}** |
| Tokens reported by {MODEL_NAME} (API check) | {measured:,} |
| Rule-of-thumb check (characters ÷ 4) | {chars / 4:,.0f} |

**Figure used for all costs below: {t:,} tokens.**

## 2. How it was estimated

1. **Tokenizer count.** The handbook text was encoded with OpenAI's `tiktoken` library using the
   `{ENCODING}` encoding, the tokenizer of OpenAI's current GPT models. Number of tokens = length of
   the encoded list = {tokens:,}.
2. **Model check.** Two requests were sent to {MODEL_NAME} through Portkey, and the `usage.input_tokens`
   field the model returns was read:
   - Request A: the handbook as instructions, plus the input "ok" → {with_hb:,} input tokens.
   - Request B: a single "." as instructions, plus the input "ok" → {without_hb:,} input tokens.
   - Handbook tokens = A − B + 1 (adding back the "." token) = {with_hb:,} − {without_hb:,} + 1 = {measured:,}.
   The chat-format overhead is the same in both requests, so the subtraction cancels it out.
3. **Sanity check.** English text averages about 4 characters per token:
   {chars:,} ÷ 4 ≈ {chars / 4:,.0f} tokens. The real count is higher ({chars / t:.2f} characters per token)
   because the handbook is mostly tables full of SKUs, prices, dollar signs, and `|` separators, which
   split into more tokens than plain prose. The rule of thumb is only a rough check and is not used for costs.

## 3. Prices ({MODEL_NAME}, from `data/prices.json`)

| Token type | $ per 1M tokens | $ per token |
|---|---|---|
| Input (not cached) | ${p["input_per_1m"]} | ${in_rate:.10f} |
| Cache write (first time the prefix is stored) | ${p["cache_write_per_1m"]} | ${write_rate:.10f} |
| Cached input (prefix read from cache) | ${p["cached_input_per_1m"]} | ${cached_rate:.10f} |

## 4. Cost of the handbook alone (input tokens only)

These figures cover only the handbook's input tokens. The vendor document, the question, and the
output tokens are extra.

### One call

| Scenario | Math | Cost |
|---|---|---|
| Without caching | {t:,} × ${p["input_per_1m"]} ÷ 1,000,000 | **{usd(one_uncached)}** |
| With caching, first call (cache write) | {t:,} × ${p["cache_write_per_1m"]} ÷ 1,000,000 | **{usd(one_write)}** |
| With caching, every later call (cache hit) | {t:,} × ${p["cached_input_per_1m"]} ÷ 1,000,000 | **{usd(one_cached)}** |

### 1,000 calls

| Scenario | Math | Cost |
|---|---|---|
| Without caching | {CALLS:,} × {usd(one_uncached)} | **{usd(k_uncached)}** |
| With caching | 1 cache write + {CALLS - 1:,} cache hits = {usd(one_write)} + {CALLS - 1:,} × {usd(one_cached)} | **{usd(k_cached)}** |
| Savings from caching | {usd(k_uncached)} − {usd(k_cached)} | **{usd(saving)}** ({saving / k_uncached:.1%} less) |

## 5. Assumptions (for the auditor)

- Token count = the `tiktoken {ENCODING}` figure ({t:,}). The API check ({measured:,}) differs by
  {abs(measured - t)} token(s).
- The handbook is sent as the **first, unchanged part** of every prompt. Caching only applies to an
  identical prefix, so the vendor document must come after the handbook.
- "With caching" assumes all 1,000 calls arrive while the cache is still warm, so only the first call
  pays the cache write. If the cache expires between batches, each new batch pays one more cache write
  ({usd(one_write)} each), which barely changes the total.
- Prices are the list prices in `data/prices.json`. Costs are in US dollars and rounded only for display.
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(md)


def p_source(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8")).get("source", "")


if __name__ == "__main__":
    main()
