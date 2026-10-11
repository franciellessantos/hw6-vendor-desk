# Problem 2 — Handbook size and cost estimate

File measured: `data/shop_handbook.md`
Model: **gpt-6-luna** (the only model used)
Prices: `data/prices.json` (OpenAI Standard pricing, per 1M tokens (MGT 409 Lecture 11))
Reproduce: `python scripts/handbook_estimate.py` from the repo root

## 1. Token count

| Measure | Value |
|---|---|
| Characters | 28,903 |
| Words (split on whitespace) | 6,127 |
| **Tokens (tiktoken `o200k_base`)** | **10,058** |
| Tokens reported by gpt-6-luna (API check) | 10,058 |
| Rule-of-thumb check (characters ÷ 4) | 7,226 |

**Figure used for all costs below: 10,058 tokens.**

## 2. How it was estimated

1. **Tokenizer count.** The handbook text was encoded with OpenAI's `tiktoken` library using the
   `o200k_base` encoding, the tokenizer of OpenAI's current GPT models. Number of tokens = length of
   the encoded list = 10,058.
2. **Model check.** Two requests were sent to gpt-6-luna through Portkey, and the `usage.input_tokens`
   field the model returns was read:
   - Request A: the handbook as instructions, plus the input "ok" → 10,069 input tokens.
   - Request B: a single "." as instructions, plus the input "ok" → 12 input tokens.
   - Handbook tokens = A − B + 1 (adding back the "." token) = 10,069 − 12 + 1 = 10,058.
   The chat-format overhead is the same in both requests, so the subtraction cancels it out.
3. **Sanity check.** English text averages about 4 characters per token:
   28,903 ÷ 4 ≈ 7,226 tokens. The real count is higher (2.87 characters per token)
   because the handbook is mostly tables full of SKUs, prices, dollar signs, and `|` separators, which
   split into more tokens than plain prose. The rule of thumb is only a rough check and is not used for costs.

## 3. Prices (gpt-6-luna, from `data/prices.json`)

| Token type | $ per 1M tokens | $ per token |
|---|---|---|
| Input (not cached) | $0.1 | $0.0000001000 |
| Cache write (first time the prefix is stored) | $0.125 | $0.0000001250 |
| Cached input (prefix read from cache) | $0.01 | $0.0000000100 |

## 4. Cost of the handbook alone (input tokens only)

These figures cover only the handbook's input tokens. The vendor document, the question, and the
output tokens are extra.

### One call

| Scenario | Math | Cost |
|---|---|---|
| Without caching | 10,058 × $0.1 ÷ 1,000,000 | **$0.001006** |
| With caching, first call (cache write) | 10,058 × $0.125 ÷ 1,000,000 | **$0.001257** |
| With caching, every later call (cache hit) | 10,058 × $0.01 ÷ 1,000,000 | **$0.000101** |

### 1,000 calls

| Scenario | Math | Cost |
|---|---|---|
| Without caching | 1,000 × $0.001006 | **$1.0058** |
| With caching | 1 cache write + 999 cache hits = $0.001257 + 999 × $0.000101 | **$0.1017** |
| Savings from caching | $1.0058 − $0.1017 | **$0.9041** (89.9% less) |

## 5. Assumptions (for the auditor)

- Token count = the `tiktoken o200k_base` figure (10,058). The API check (10,058) differs by
  0 token(s).
- The handbook is sent as the **first, unchanged part** of every prompt. Caching only applies to an
  identical prefix, so the vendor document must come after the handbook.
- "With caching" assumes all 1,000 calls arrive while the cache is still warm, so only the first call
  pays the cache write. If the cache expires between batches, each new batch pays one more cache write
  ($0.001257 each), which barely changes the total.
- Prices are the list prices in `data/prices.json`. Costs are in US dollars and rounded only for display.
