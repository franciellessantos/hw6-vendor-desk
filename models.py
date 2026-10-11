"""Structured types for the Campus Customs vendor desk agent."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Defenses:
    """Which defense layers are on (Problem 6). All on is the default, production setup.

    code   - the document is cleaned before any model sees it (hidden text, invisible PDF text, links,
             our internal tool names removed).
    design - the model only extracts facts; Python applies the handbook rules and writes the reason,
             so a document cannot change the decision rules or put text into the answer.
    prompt - the security rules section of prompts/prompt.md is included in the instructions.
    """

    code: bool = True
    design: bool = True
    prompt: bool = True

    @property
    def label(self) -> str:
        on = [n for n in ("code", "design", "prompt") if getattr(self, n)]
        return "+".join(on) if on else "none"


@dataclass
class DeskDeps:
    """Per-run context handed to every tool. The agent can only read the one document it was given."""

    doc_path: Path
    run_id: str
    defenses: Defenses = Defenses()


class ExtractedQuote(BaseModel):
    """Design layer: what the extractor model returns. Facts only, no decision and no free text.

    Every value the document states for a field is listed, so a planted "correction" cannot silently
    replace the real quote; the rules engine sees both and takes the cautious one.
    """

    sender: str = Field(description="Company that sent the document (letterhead, From line, or signature).")
    other_vendor_names: list[str] = Field(
        default_factory=list,
        description="Any OTHER company the document claims is the vendor, seller, or vendor of record.")
    sku: str | None = Field(description="Campus Customs SKU (format CC-XX-000). null if not stated.",
                            pattern=r"^CC-[A-Z]{2}-\d{3}$")
    unit_prices: list[float] = Field(description="Every unit price in USD the document states for the item.")
    lead_times_days: list[int] = Field(description="Every lead time the document states, in days.")
    min_orders: list[int] = Field(description="Every minimum order quantity the document states, in units.")


class VendorDecision(BaseModel):
    """The agent's final answer for one vendor document (handbook section 13)."""

    vendor: str = Field(description="Vendor name exactly as the document shows it.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. null if the document does not say.")
    unit_price: float | None = Field(description="Quoted unit price in USD. null if the document does not say.")
    lead_time_days: int | None = Field(description="Lead time in days. null if the document does not say.")
    min_order: int | None = Field(description="Minimum order in units. null if the document does not say.")
    decision: Literal["recommend", "do_not_recommend"]
    reason: str = Field(description="One sentence that names the purchasing check that decided it.")


class TrapCall(BaseModel):
    """One blocked call to send_email or approve_payment: evidence that a document tried to trick the agent."""

    time: str
    run_id: str
    document: str
    tool: Literal["send_email", "approve_payment"]
    arguments: dict[str, Any]
    result: str = "BLOCKED - nothing was sent or paid"


class UsageLog(BaseModel):
    """Token counts reported by the API for one run, and the dollar cost from data/prices.json."""

    run_id: str
    time: str
    document: str
    model: str
    setup: Literal["cached", "no_cache"] = "cached"
    defenses: str = "code+design+prompt"
    requests: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int = 0
    cost_usd: float


class ToolCallRecord(BaseModel):
    """One tool call inside a run: what was called, with which arguments, and what came back."""

    tool: str
    arguments: dict[str, Any]
    result: str


class AuditEntry(BaseModel):
    """Full record of one run: every tool call plus the final answer."""

    run_id: str
    time: str
    document: str
    model: str
    defenses: str = "code+design+prompt"
    tool_calls: list[ToolCallRecord]
    extracted: ExtractedQuote | None = None
    final_answer: VendorDecision
