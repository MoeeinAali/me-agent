"""Step ⑥: keep only what the evidence supports, then choose the capability in code."""

from dataclasses import dataclass, field

from app.domain import Capability, Claim, Evidence, Lang
from app.pipeline.generate import GenerationOut
from app.pipeline.policy import PolicyDecision

REGENERATE_ABOVE = 0.30
_API_SOURCES = {"github", "hrcando", "link_check"}


MISSING_ITEM_CHARS = 80
MISSING_ITEMS = 3

_NOT_PUBLISHED = {
    "en": "That isn't in Moeein's published record, so I can't answer it.",
    "fa": "این مورد در رکورد منتشرشدهٔ معین نیست، پس نمی‌توانم به آن پاسخ دهم.",
}
_MISSING_NOTE = {"en": "Not in the record: {items}.", "fa": "در رکورد نیست: {items}."}


@dataclass
class VerifyResult:
    claims_kept: list[Claim]
    dropped: list[Claim] = field(default_factory=list)
    drop_ratio: float = 0.0

    @property
    def needs_regen(self) -> bool:
        return self.drop_ratio > REGENERATE_ABOVE


def verify(out: GenerationOut, evidence: list[Evidence]) -> VerifyResult:
    """A claim survives only if it cites at least one existing, trusted evidence item."""
    trusted = {e.id for e in evidence if e.trusted}
    kept, dropped = [], []
    for claim in out.claims:
        cited = [eid for eid in claim.evidence if eid in trusted]
        if cited:
            kept.append(claim.model_copy(update={"evidence": cited}))
        else:
            dropped.append(claim)
    ratio = len(dropped) / len(out.claims) if out.claims else 0.0
    return VerifyResult(claims_kept=kept, dropped=dropped, drop_ratio=ratio)


def compose_answer(kept: list[Claim], missing: list[str], language: Lang) -> str:
    """The visitor-facing text, built only from verified claims plus fixed, localized notes.

    Model prose never reaches the visitor directly: with no surviving claims the reply is a
    fixed refusal, and ``missing`` items are truncated so they can't smuggle in statements.
    """
    body = ""
    previous: str | None = None
    for claim in kept:
        text = claim.text.strip()
        if previous is not None:
            is_bullet = text.startswith("- ") or previous.startswith("- ")
            body += "\n" if is_bullet else " "
        body += text
        previous = text
    if not kept:
        body = _NOT_PUBLISHED[language]
    items = [m.strip()[:MISSING_ITEM_CHARS] for m in missing if m.strip()][:MISSING_ITEMS]
    if items:
        separator = "، " if language == "fa" else ", "
        body = f"{body} {_MISSING_NOTE[language].format(items=separator.join(items))}"
    return body


def decide_capability(
    decision: PolicyDecision, kept: list[Claim], evidence: list[Evidence]
) -> Capability:
    if decision.capability is not None:
        return decision.capability
    if not kept:
        return "refuse_unpublished"
    source = {e.id: e.source for e in evidence}
    if any(source.get(eid) in _API_SOURCES for claim in kept for eid in claim.evidence):
        return "answer_from_api"
    return "answer_from_record"
