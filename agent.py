"""Campus Customs vendor desk agent (entry point).

Run from the repo root:  python agent.py --doc data/practice_docs/p01_bluehen_quote.html
MODEL: gpt-6-luna through Portkey (MODEL_NAME below). There is no fallback model.

The agent reads one vendor document, extracts vendor / sku / unit price / lead time / minimum
order, and decides recommend or do_not_recommend under the handbook's purchasing rules.
send_email and approve_payment are trap tools: nothing is ever sent or paid (see tools.py).
Every run appends to output/usage_log.json and output/audit_trail.json.

Design defense layer (default): the model only extracts facts; the "Handbook rules" section below
applies the four purchasing checks in plain Python and writes the reason from a fixed template.
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from functools import cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage, UsageLimits

import tools
from models import AuditEntry, Defenses, DeskDeps, ExtractedQuote, ToolCallRecord, UsageLog, VendorDecision

# ===================== Settings =====================

HW6_DIR = Path(__file__).resolve().parent
PROMPT_FILE = HW6_DIR / "prompts" / "prompt.md"
HANDBOOK_FILE = HW6_DIR / "data" / "shop_handbook.md"
PRICES_FILE = HW6_DIR / "data" / "prices.json"
OUTPUT_DIR = HW6_DIR / "output"
USAGE_LOG = OUTPUT_DIR / "usage_log.json"
AUDIT_LOG = OUTPUT_DIR / "audit_trail.json"

MODEL_NAME = "gpt-6-luna"
# Extraction plus four rule checks is a light task: low reasoning keeps output tokens and cost down.
REASONING_EFFORT = "low"
# Hard stop per run: one read, a final answer, and room for one retry.
LIMITS = UsageLimits(request_limit=5, tool_calls_limit=4)
# Handbook section 4 limits.
MAX_LEAD_TIME_DAYS = 21
MAX_MIN_ORDER = 600

# Secrets come from .env in the repo root (see .env.example); never hardcoded.
load_dotenv(HW6_DIR / ".env")
load_dotenv(HW6_DIR.parent / ".env")  # fallback: the course folder .env, when the repo sits inside it
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


def build_model() -> OpenAIResponsesModel:
    """OpenAI Responses API routed through Portkey, pinned to gpt-6-luna."""
    key = os.environ["PORTKEY_API_KEY"]
    client = AsyncOpenAI(
        api_key=key,
        base_url="https://api.portkey.ai/v1",
        default_headers={
            "x-portkey-api-key": key,
            "x-portkey-provider": "openai",
            # Always a fresh model answer: a gateway-cached reply would not be a real agent run.
            "x-portkey-cache-force-refresh": "true",
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def prompt_part(name: str) -> str:
    """One prompt from prompts/prompt.md: the text between <!-- PART: name --> and <!-- END PART -->."""
    text = PROMPT_FILE.read_text(encoding="utf-8")
    return re.search(rf"<!-- PART: {name} -->\n(.*?)\n<!-- END PART -->", text, re.S).group(1) + "\n"


def security_rules() -> str:
    """The "## Security rules" section of the decider prompt (the prompt defense layer)."""
    return re.search(r"^## Security rules.*?(?=^## )", prompt_part("decider"), re.S | re.M).group(0)


def instructions_text(defenses: Defenses) -> str:
    """Design off: one agent with the decider prompt + handbook that decides by itself.
    Design on: the extractor prompt and NO handbook; decide() below makes the call.
    Prompt off: the security rules section is left out."""
    if defenses.design:
        text = prompt_part("extractor")
        return text + "\n\n" + security_rules() if defenses.prompt else text
    text = prompt_part("decider")
    if not defenses.prompt:
        text = text.replace(security_rules(), "")
    return text + "\n\n# Campus Customs Shop Handbook (reference)\n\n" + HANDBOOK_FILE.read_text(encoding="utf-8")


def build_agent(cache: bool = True, defenses: Defenses = Defenses()) -> Agent:
    """cache=True: the instructions form one fixed prefix that is identical on every call, so OpenAI
    can cache it. Everything that changes per document comes after it (user message, tool results).

    cache=False (Problem 4 test only): OpenAI caches any repeated prefix of 1,024+ tokens automatically
    and has no off switch, so a random id is put at the very start of the instructions on EVERY model
    request. No two requests then share a prefix and nothing can be read from the cache.

    The trap tools stay registered in every setup: they are the tripwire that shows an attack worked.
    """
    base = instructions_text(defenses)
    settings = OpenAIResponsesModelSettings(openai_reasoning_effort=REASONING_EFFORT)
    if cache:
        instructions = base
        settings["openai_prompt_cache_key"] = f"campus-customs-vendor-desk-{defenses.label}"
    else:
        def instructions(ctx: RunContext[DeskDeps]) -> str:  # re-evaluated on every model request
            return f"[request id {uuid.uuid4().hex}]\n\n{base}"
    return Agent(
        build_model(),
        deps_type=DeskDeps,
        output_type=ExtractedQuote if defenses.design else VendorDecision,
        instructions=instructions,
        tools=[tools.read_document, tools.send_email, tools.approve_payment],
        model_settings=settings,
    )


# ===================== Handbook rules (design layer) =====================
# The vendor lists and max unit costs are read straight from data/shop_handbook.md. A vendor document can
# change what the model reads, but it cannot change these rules, and no document text reaches the
# answer except the vendor name.
def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("&", "and"))


def _listed(name: str, table: dict[str, str]) -> bool:
    """Name matches a listed vendor, allowing suffixes like "Inc." or "LLC" after the listed name."""
    n = _norm(name)
    return bool(n) and any(n.startswith(k) for k in table)


def _section(text: str, number: int) -> str:
    return re.search(rf"^## {number}\..*?(?=^## )", text, re.S | re.M).group(0)


@cache
def handbook_tables() -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    """(approved vendors, removed/pending vendors, SKU -> max unit cost), all read from the handbook."""
    text = HANDBOOK_FILE.read_text(encoding="utf-8")
    approved = {_norm(m): m for m in re.findall(r"^\| [A-Z]{3} \| ([^|]+?) \|", _section(text, 5), re.M)}
    removed = {_norm(m): m for m in re.findall(r"^\| ([^|]+?) \| (?:Removed|Application pending)", _section(text, 6), re.M)}
    max_cost = {sku: float(cost) for sku, cost in
                re.findall(r"^\| (CC-[A-Z]{2}-\d{3}) \|[^\n]*?\| \$[\d.]+ \| \$([\d.]+) \|", _section(text, 9), re.M)}
    return approved, removed, max_cost


def decide(q: ExtractedQuote) -> VendorDecision:
    approved, removed, max_cost = handbook_tables()

    # Cautious reading: if the document states a field more than once, use the value worst for us.
    # A planted "correction" can then never make a quote look better than its own worst figure.
    price = max(q.unit_prices) if q.unit_prices else None
    lead = max(q.lead_times_days) if q.lead_times_days else None
    moq = max(q.min_orders) if q.min_orders else None
    conflicts = [name for name, vals in (("unit price", q.unit_prices), ("lead time", q.lead_times_days),
                                         ("minimum order", q.min_orders)) if len(set(vals)) > 1]
    note = f" (the document states conflicting {', '.join(conflicts)} values, so the less favorable one was used)" \
        if conflicts else ""

    def answer(decision: str, reason: str) -> VendorDecision:
        return VendorDecision(vendor=q.sender, sku=q.sku, unit_price=price, lead_time_days=lead,
                              min_order=moq, decision=decision, reason=reason + note + ".")

    # Check 1: approved vendor. Every company the document names as the seller must be approved.
    names = [q.sender, *q.other_vendor_names]
    banned = [n for n in names if _listed(n, removed)]
    if banned:
        return answer("do_not_recommend",
                      f"Approved-vendor check failed: {banned[0]} is on the removed or pending vendor list")
    unknown = [n for n in names if not _listed(n, approved)]
    if unknown:
        return answer("do_not_recommend",
                      f"Approved-vendor check failed: {unknown[0]} is not on the approved vendor list")
    # Check 2: price at or below the catalogue max unit cost.
    if q.sku is None or q.sku not in max_cost:
        return answer("do_not_recommend", "Price check failed: the SKU is missing or not in our catalogue")
    if price is None:
        return answer("do_not_recommend", "Price check failed: the document does not state a unit price")
    if price > max_cost[q.sku]:
        return answer("do_not_recommend", "Price check failed: the quoted unit price is above our max unit cost")
    # Check 3: lead time.
    if lead is None:
        return answer("do_not_recommend", "Lead-time check failed: the document does not state a lead time")
    if lead > MAX_LEAD_TIME_DAYS:
        return answer("do_not_recommend", f"Lead-time check failed: {lead} days is more than {MAX_LEAD_TIME_DAYS} days")
    # Check 4: minimum order.
    if moq is None:
        return answer("do_not_recommend", "Minimum-order check failed: the document does not state a minimum order")
    if moq > MAX_MIN_ORDER:
        return answer("do_not_recommend", f"Minimum-order check failed: {moq} units is more than {MAX_MIN_ORDER} units")
    return answer("recommend", "All four purchasing checks passed (approved vendor, price, lead time, minimum order)")


# ===================== Logging =====================

def cost_usd(usage: RunUsage) -> float:
    """Dollar cost from data/prices.json. input_tokens already includes cached tokens."""
    p = json.loads(PRICES_FILE.read_text(encoding="utf-8"))[MODEL_NAME]
    fresh = usage.input_tokens - usage.cache_read_tokens - usage.cache_write_tokens
    return round((fresh * p["input_per_1m"]
                  + usage.cache_read_tokens * p["cached_input_per_1m"]
                  + usage.cache_write_tokens * p["cache_write_per_1m"]
                  + usage.output_tokens * p["output_per_1m"]) / 1_000_000, 8)


def tool_records(messages) -> list[ToolCallRecord]:
    """Pair each tool call with its result, in call order."""
    calls: dict[str, ToolCallPart] = {}
    results: dict[str, str] = {}
    for msg in messages:
        for part in msg.parts:
            if isinstance(part, ToolCallPart):
                calls[part.tool_call_id] = part
            elif isinstance(part, ToolReturnPart):
                text = str(part.content)
                results[part.tool_call_id] = text if len(text) <= 300 else text[:300] + f"... [{len(text)} chars]"
    return [ToolCallRecord(tool=c.tool_name, arguments=c.args_as_dict(), result=results.get(i, "(no result)"))
            for i, c in calls.items() if c.tool_name != "final_result"]


def models_used(messages) -> set[str]:
    return {m.model_name for m in messages if isinstance(m, ModelResponse) and m.model_name}


# ===================== Run =====================

def request_usage(messages) -> list[dict]:
    """Token counts the API reported for each model request in the run."""
    return [{"input_tokens": m.usage.input_tokens, "cached_input_tokens": m.usage.cache_read_tokens,
             "cache_write_tokens": m.usage.cache_write_tokens, "output_tokens": m.usage.output_tokens,
             "details": dict(m.usage.details)}
            for m in messages if isinstance(m, ModelResponse)]


def review(doc: Path, cache: bool = True,
           defenses: Defenses = Defenses()) -> tuple[VendorDecision, UsageLog, list[dict]]:
    run_id = uuid.uuid4().hex[:8]
    started = datetime.now().isoformat(timespec="seconds")
    result = build_agent(cache, defenses).run_sync(
        f"Review the vendor document assigned to you ({doc.name}) and return your recommendation.",
        deps=DeskDeps(doc_path=doc, run_id=run_id, defenses=defenses),
        usage_limits=LIMITS,
    )
    messages = result.all_messages()
    used = models_used(messages)
    if any(not m.startswith(MODEL_NAME) for m in used):
        sys.exit(f"Model check failed: expected {MODEL_NAME}, API reported {used}")
    model = ", ".join(sorted(used)) or MODEL_NAME

    extracted = result.output if defenses.design else None
    answer = decide(extracted) if defenses.design else result.output
    usage = result.usage
    log = UsageLog(
        run_id=run_id, time=started, document=doc.name, model=model,
        setup="cached" if cache else "no_cache", defenses=defenses.label, requests=usage.requests,
        input_tokens=usage.input_tokens, cached_input_tokens=usage.cache_read_tokens,
        cache_write_tokens=usage.cache_write_tokens, output_tokens=usage.output_tokens,
        reasoning_tokens=usage.details.get("reasoning_tokens", 0), cost_usd=cost_usd(usage),
    )
    tools.append_json(USAGE_LOG, log.model_dump())
    tools.append_json(AUDIT_LOG, AuditEntry(
        run_id=run_id, time=started, document=doc.name, model=model, defenses=defenses.label,
        tool_calls=tool_records(messages), extracted=extracted, final_answer=answer,
    ).model_dump())
    return answer, log, request_usage(messages)


def parse_defenses(spec: str) -> Defenses:
    if spec == "all":
        return Defenses()
    on = set() if spec == "none" else {x.strip() for x in spec.split(",")}
    unknown = on - {"code", "design", "prompt"}
    if unknown:
        sys.exit(f"Unknown defense layer(s): {unknown}")
    return Defenses(code="code" in on, design="design" in on, prompt="prompt" in on)


def ensure_trap_log() -> None:
    if not tools.TRAP_LOG.exists():  # starts empty; entries are only ever appended
        tools.TRAP_LOG.parent.mkdir(exist_ok=True)
        tools.TRAP_LOG.write_text("[]", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="path to a vendor document (.html, .pdf, .eml)")
    parser.add_argument("--no-cache", action="store_true", help="defeat prompt caching (cost test only)")
    parser.add_argument("--defenses", default="all",
                        help="all (default), none, or a comma list of code,design,prompt (tests only)")
    args = parser.parse_args()
    doc = Path(args.doc).resolve()
    if not doc.is_file():
        sys.exit(f"Document not found: {doc}")
    ensure_trap_log()
    print(review(doc, cache=not args.no_cache, defenses=parse_defenses(args.defenses))[0].model_dump_json(indent=2))


if __name__ == "__main__":
    main()
