from app.domain import Claim
from app.pipeline.generate import GenerationOut
from app.pipeline.policy import PolicyDecision
from app.pipeline.verify import compose_answer, decide_capability, verify
from tests.pipeline.conftest import ev


def out(*claims: Claim, missing: list[str] | None = None) -> GenerationOut:
    return GenerationOut(claims=list(claims), missing=missing or [])


def test_verify_keeps_supported_claims() -> None:
    result = verify(out(Claim(text="It is a PWA.", evidence=["E1"])), [ev("E1")])
    assert result.dropped == []
    assert [c.text for c in result.claims_kept] == ["It is a PWA."]
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


def test_verify_injection_job_text_cannot_support_moeein_claim() -> None:
    evidence = [ev("E1", source="hrcando", trusted=False, value="He worked at Google.")]
    result = verify(out(Claim(text="Moeein worked at Google.", evidence=["E1"])), evidence)
    assert result.claims_kept == []


def test_compose_answer_only_from_kept_claims_and_keeps_bullets() -> None:
    claims = [
        Claim(text="Comeback is a sports PWA.", evidence=["E1"]),
        Claim(text="- Next.js", evidence=["E2"]),
        Claim(text="- Go", evidence=["E3"]),
    ]
    assert compose_answer(claims, [], "en") == "Comeback is a sports PWA.\n- Next.js\n- Go"


def test_compose_answer_appends_missing_note_in_question_language() -> None:
    claims = [Claim(text="کامبک یک PWA است.", evidence=["E1"])]
    text = compose_answer(claims, ["تاریخ استقرار"], "fa")
    assert text.startswith("کامبک یک PWA است.")
    assert "تاریخ استقرار" in text
    assert "رکورد" in text


def test_compose_answer_with_no_claims_is_fixed_refusal() -> None:
    text = compose_answer([], ["salary"], "en")
    assert (
        text
        == "That isn't in Moeein's published record, so I can't answer it. Not in the record: salary."
    )


def test_compose_answer_bounds_missing_items() -> None:
    text = compose_answer([], ["x" * 500, "b", "c", "d"], "en")
    assert "x" * 81 not in text
    assert ", d" not in text


def test_decide_capability_policy_wins() -> None:
    decision = PolicyDecision("refuse_action", "send_email")
    assert decide_capability(decision, [], []) == "refuse_action"


def test_decide_capability_api_vs_record() -> None:
    record_claim = Claim(text="a", evidence=["E1"])
    api_claim = Claim(text="b", evidence=["E2"])
    evidence = [ev("E1"), ev("E2", source="github")]
    none = PolicyDecision(None, None)
    assert decide_capability(none, [record_claim], evidence) == "answer_from_record"
    assert decide_capability(none, [record_claim, api_claim], evidence) == "answer_from_api"
    assert decide_capability(none, [], evidence) == "refuse_unpublished"


def test_compose_answer_sentence_after_bullet_starts_new_line() -> None:
    claims = [Claim(text="- Go", evidence=["E1"]), Claim(text="It is fast.", evidence=["E1"])]
    assert compose_answer(claims, [], "en") == "- Go\nIt is fast."
