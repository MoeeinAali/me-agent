"""Step ⑥: keep only what the evidence supports, then choose the capability in code."""

from dataclasses import dataclass, field

from app.domain import Capability, Claim, Evidence
from app.pipeline.generate import GenerationOut
from app.pipeline.policy import PolicyDecision

REGENERATE_ABOVE = 0.30
_API_SOURCES = {"github", "hrcando", "link_check"}


@dataclass
class VerifyResult:
    answer: str
    claims_kept: list[Claim]
    dropped: list[Claim] = field(default_factory=list)
    drop_ratio: float = 0.0

    @property
    def needs_regen(self) -> bool:
        return self.drop_ratio > REGENERATE_ABOVE


def verify(out: GenerationOut, evidence: list[Evidence]) -> VerifyResult:
    """A claim survives only if it cites at least one existing, trusted evidence item.

    When anything is dropped the answer is rebuilt from the surviving claims, so unsupported text
    can never reach the visitor even if it was woven into the model's prose.
    """
    trusted = {e.id for e in evidence if e.trusted}
    kept, dropped = [], []
    for claim in out.claims:
        cited = [eid for eid in claim.evidence if eid in trusted]
        if cited:
            kept.append(claim.model_copy(update={"evidence": cited}))
        else:
            dropped.append(claim)
    ratio = len(dropped) / len(out.claims) if out.claims else 0.0
    answer = out.answer if not dropped else " ".join(c.text.strip() for c in kept)
    return VerifyResult(answer=answer, claims_kept=kept, dropped=dropped, drop_ratio=ratio)


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
