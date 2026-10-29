"""LLM-as-judge for groundedness: is each claim actually supported by the evidence it cites?
Uses a model from a different family than the generator, to avoid grading its own work."""

from pydantic import BaseModel

from app.domain import Claim, Evidence
from app.llm.client import LLM

SYSTEM = (
    "You check whether a claim is fully supported by the evidence quoted with it. Answer "
    "supported=true only if every fact in the claim appears in the evidence. Paraphrase and "
    "translation are fine; any extra fact (a date, number, employer, skill) makes it false."
)


class Verdict(BaseModel):
    supported: bool


async def judge_claims(
    llm: LLM, model: str, claims: list[Claim], evidence: list[Evidence]
) -> list[bool]:
    by_id = {e.id: e.value for e in evidence}
    verdicts = []
    for claim in claims:
        quoted = "\n".join(f"- {by_id[i]}" for i in claim.evidence if i in by_id)
        out, _ = await llm.structured(
            model,
            SYSTEM,
            [{"role": "user", "content": f"Evidence:\n{quoted}\n\nClaim: {claim.text}"}],
            Verdict,
        )
        verdicts.append(out.supported)
    return verdicts
