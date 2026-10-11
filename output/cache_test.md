# Problem 4 — With and without cached tokens

**Hypothesis:** the model can reuse the same handbook on every call (prompt caching), so the vendor desk
spends less money.

**Result:** confirmed. With caching, the 12 practice docs cost **$0.00383**. Without caching they cost
**$0.03392**, so caching saved **88.7%**.

Raw data: `output/cache_test.json`, which has every run, every token count the API reported (per run and
per model request), and the cost of each run.
Reproduce: `python scripts/cache_test.py` from the repo root. Model: **gpt-6-luna** (API reported `gpt-6-luna-global`),
low reasoning effort.

## Setups

| Setup | How it works | Proof it worked |
|---|---|---|
| **cached** | Prompt + handbook go first, identical on every request, with a `prompt_cache_key`. | 262,423 of 267,341 input tokens (98.2%) were read from cache. |
| **no_cache** | OpenAI caches any repeated prefix of 1,024+ tokens automatically and has no off switch. To defeat it, a random id is placed at the start of the instructions on **every** request, so no two requests share a prefix. | The API reported **0 cached tokens on all 24 requests**, so every no_cache run is valid (`"valid": true` in the JSON). |

Each document takes **2 model requests**. Request 1 calls `read_document`; request 2 returns the answer.

Cost formula, using `data/prices.json`, per 1M tokens: input $0.10, cached input $0.01, cache write
$0.125, output $0.50.

```
cost = (fresh_input × 0.10 + cached × 0.01 + cache_write × 0.125 + output × 0.50) / 1,000,000
fresh_input = input_tokens − cached − cache_write
```

## 1. Total cost per setup (12 docs)

| Setup | Requests | Input tokens | Cached | Cache write | Fresh input | Output (reasoning) | **Total cost** |
|---|---|---|---|---|---|---|---|
| cached | 24 | 267,341 | 262,423 | 1,894 | 3,024 | 1,340 (289) | **$0.00383339** |
| no_cache | 24 | 267,897 | 0 | 264,873 | 3,024 | 1,022 (0) | **$0.03392251** |

**Saved by caching: $0.03392251 − $0.00383339 = $0.03008912, which is 88.7% less.**

## 2. Cost per document

| Setup | Math | **Cost per doc** |
|---|---|---|
| cached | $0.00383339 ÷ 12 | **$0.00031945** |
| no_cache | $0.03392251 ÷ 12 | **$0.00282688** |

**Saved per doc: $0.00250743, which is 88.7% less.** With caching, one doc costs about 1/9 as much.

| Doc | cached | no_cache | Saved |
|---|---|---|---|
| p01_bluehen_quote.html | $0.000281 | $0.002820 | 90.0% |
| p02_elmcity_quote.html | $0.000311 | $0.002828 | 89.0% |
| p03_ivyprint_catalog.html | $0.000311 | $0.002826 | 89.0% |
| p04_harborstitch_quote.html | $0.000307 | $0.002824 | 89.1% |
| p05_maplemills_quote.pdf | $0.000307 | $0.002828 | 89.1% |
| p06_qtextile_quote.pdf | $0.000321 | $0.002838 | 88.7% |
| p07_longwharf_quote.pdf | $0.000314 | $0.002829 | 88.9% |
| p08_chapelst_email.eml | $0.000282 | $0.002822 | 90.0% |
| p09_westville_email.eml | $0.000317 | $0.002830 | 88.8% |
| p10_eastrock_email.eml | $0.000462 | $0.002824 | 83.6% |
| p11_yorkst_quote.html | $0.000306 | $0.002824 | 89.2% |
| p12_bluehen_quote.pdf | $0.000314 | $0.002830 | 88.9% |

## 3. Real numbers vs. the Problem 2 estimate

Problem 2 priced **one call carrying only the handbook (10,058 tokens)**. Real runs cost more because a
document needs more than that:

| | Problem 2 estimate (handbook, 1 call) | Real cost per doc | Real ÷ estimate |
|---|---|---|---|
| Without cache | $0.001006 | $0.002827 | **2.8×** |
| With cache | $0.000101 (cache hit) | $0.000319 | **3.2×** |
| Savings from caching | 89.9% (over 1,000 calls) | 88.7% | about the same |

The savings percentage was predicted almost exactly. The dollar amounts are about 3× higher because:

1. **Two requests per doc, not one.** The agent reads the document with a tool and then answers, and the
   handbook is sent again on the second request. That doubles the cost (×2).
2. **More than the handbook.** Each request is about 11,150 input tokens, not 10,058. The agent prompt,
   the three tool definitions, the output schema, and the document text add about 1,100 tokens (×1.1).
3. **"No cache" is billed as cache write, not plain input.** The API wrote every no_cache prefix to the
   cache at $0.125/1M instead of charging $0.10/1M (×1.25). Check: $0.001006 × 2 × 1.1 × 1.25 ≈
   $0.00277 per doc, close to the real $0.00283.
4. **Output tokens.** The Problem 2 estimate left them out. They are small without caching (1.5% of cost)
   but large with caching (17.5% of cost).

## 4. Projection: 1,000 docs a day for 30 days (30,000 docs)

Using the measured cost per doc:

| Setup | Math | Per day (1,000 docs) | **30 days (30,000 docs)** |
|---|---|---|---|
| cached | 30,000 × $0.00031945 | $0.32 | **$9.58** |
| no_cache | 30,000 × $0.00282688 | $2.83 | **$84.81** |
| Savings | $84.81 − $9.58 | $2.51 | **$75.22 (88.7%)** |

For reference, if a provider charged the plain $0.10/1M input rate with no cache-write surcharge,
no-caching would cost $0.00227 per doc, or **$68.25 for 30 days**. Caching still saves 86% against that.

## 5. What surprised me and why

1. **Turning caching off cost more than plain input.** I expected the no_cache run to pay $0.10/1M on
   every input token. Instead, the API reported about 265k **cache-write** tokens at $0.125/1M. The model
   still stores each new prefix in the cache; my random id just guarantees nothing is ever read back. So
   "no cache" means paying the 25% write premium on every call and never getting the 90% discount. This
   is the worst case. Caching is not free, and it only pays off when the prefix is reused.
2. **The handbook is paid for twice per document.** Tool use means two model requests per doc, and each
   request resends the full prompt and handbook (about 11k tokens). Problem 2 priced one call. Caching
   matters even more for multi-step agents because every extra step resends the same prefix.
3. **With caching, output tokens become a big share of the bill.** Output is 50× more expensive than
   cached input ($0.50 vs $0.01 per 1M), so 1,340 output tokens (17.5% of the cached cost) cost almost as
   much as 67,000 cached input tokens. p10 was the most expensive cached doc ($0.000462): the model used
   289 reasoning tokens, the only reasoning tokens in all 24 runs. Once the handbook is cached, short
   answers and low reasoning effort are the next cost lever.
4. **p01 and p08 wrote nothing to the cache.** Every other cached doc wrote about 190 tokens, the
   document text plus the agent's tool call. p01 and p08 were already run in Problem 3 a few minutes
   earlier, so their whole request, document included, was still cached. The cache keeps whatever prefix
   it has seen recently, not just the handbook.
5. **Accuracy slipped once, and caching did not cause it.** Cached runs got 11/12 right and no_cache runs
   12/12. In the cached p10 run, the model treated East Rock's honest "corrected quote" email as a
   manipulation attempt, set the price to unknown, and answered do_not_recommend. The no_cache run of the
   same doc got it right. The cache only changes how the input is billed, not what the model sees, so
   this is normal run-to-run variation. My security rule in `prompts/prompt.md` ("correction" = attack)
   is too broad. It should only distrust corrections that contradict the price shown in the same document
   (like p07 and p12), not a whole email that replaces an older quote.
6. **No trap calls.** `output/trap_calls.json` is still empty after 24 runs that included p04, p06, and
   p09, which ask for a payment, an email, and a tracking link.
