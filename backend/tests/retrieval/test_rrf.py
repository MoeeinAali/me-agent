from app.retrieval.hybrid import rrf
from app.retrieval.normalize import normalize


def test_rrf_orders_by_fused_rank() -> None:
    fused = rrf([["a", "b"], ["b", "c"]])
    assert fused[0][0] == "b"
    assert [i for i, _ in fused] == ["b", "a", "c"]


def test_normalize_persian_variants() -> None:
    assert normalize("كامبك") == normalize("کامبک")
    assert normalize("می‌خواهم") == normalize("میخواهم")
    assert normalize("  Comeback\tPWA ") == "comeback pwa"
