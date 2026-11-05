from app.pipeline.run import inline_job, match_pending

OPTIONS = [
    {"entity_id": "project:comeback", "kind": "project", "label": "Comeback"},
    {"entity_id": "project:arcadia", "kind": "project", "label": "Arcadia"},
]


def test_match_by_name_and_short_ordinal() -> None:
    assert match_pending("Arcadia please", OPTIONS) == 1
    assert match_pending("the second one", OPTIONS) == 1
    assert match_pending("دومی", OPTIONS) == 1


def test_a_number_inside_a_new_question_is_not_a_pick() -> None:
    assert match_pending("does he have 1 year of experience with Go?", OPTIONS) is None


def test_inline_job() -> None:
    url = "https://career.hrcando.ir/co/Milli/job-detail/6867af3e-e373-4659-85a8-a9420cd14388"
    assert inline_job(f"fit for this? {url}.") == {"job_url": url}
    assert inline_job("Is he a fit for a backend role?") is None
    long = "Would he fit a backend role needing 3 years of Go, PostgreSQL and Kubernetes?"
    assert inline_job(long) == {"job_text": long}
