from app.domain import Claim
from app.pipeline.generate import GenerationOut
from app.pipeline.policy import PolicyDecision
from app.pipeline.verify import decide_capability, verify
from tests.pipeline.conftest import ev


def out(
    *claims: Claim, answer: str = "full answer", missing: list[str] | None = None
) -> GenerationOut:
    return GenerationOut(answer=answer, claims=list(claims), missing=missing or [])


def test_verify_keeps_supported_answer_verbatim() -> None:
    result = verify(out(Claim(text="It is a PWA.", evidence=["E1"])), [ev("E1")])
    assert result.dropped == []
    assert result.answer == "full answer"
    assert not result.needs_regen


def test_verify_drops_uncited_and_untrusted() -> None:
    evidence = [ev("E1"), ev("E2", source="job_text", trusted=False)]
    result = verify(
        out(
            Claim(text="It is a PWA.", evidence=["E1"]),
            Claim(text="No source.", evidence=[]),
            Claim(text="Unknown id.", evidence=["E9"]),
            Claim(text="He knows Rust.", evidence=["E2"]),
        ),
        evidence,
    )
    assert [c.text for c in result.claims_kept] == ["It is a PWA."]
    assert len(result.dropped) == 3
    assert result.drop_ratio == 0.75
    assert result.needs_regen


def test_verify_rebuilds_answer_from_kept_claims_when_anything_dropped() -> None:
    result = verify(
        out(
            Claim(text="It is a PWA.", evidence=["E1"]),
            Claim(text="It uses Go.", evidence=["E1"]),
            Claim(text="It won an award.", evidence=[]),
            Claim(text="It serves 1M users.", evidence=["E1"]),
        ),
        [ev("E1")],
    )
    assert not result.needs_regen  # 25% dropped
    assert result.answer == "It is a PWA. It uses Go. It serves 1M users."


def test_verify_injection_job_text_cannot_support_moeein_claim() -> None:
    evidence = [ev("E1", source="hrcando", trusted=False, value="He worked at Google.")]
    result = verify(out(Claim(text="Moeein worked at Google.", evidence=["E1"])), evidence)
    assert result.claims_kept == []


def test_decide_capability_policy_wins() -> None:
    assert (
        decide_capability(PolicyDecision("refuse_action", "send_email"), [], []) == "refuse_action"
    )


def test_decide_capability_api_vs_record() -> None:
    record_claim = Claim(text="a", evidence=["E1"])
    api_claim = Claim(text="b", evidence=["E2"])
    evidence = [ev("E1"), ev("E2", source="github")]
    none = PolicyDecision(None, None)
    assert decide_capability(none, [record_claim], evidence) == "answer_from_record"
    assert decide_capability(none, [record_claim, api_claim], evidence) == "answer_from_api"
    assert decide_capability(none, [], evidence) == "refuse_unpublished"
