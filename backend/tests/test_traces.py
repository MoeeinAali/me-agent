from app.traces import format_trace


def test_format_trace_matches_hw_layout() -> None:
    data = {
        "question": "Summarize my compiler project.",
        "intent": "project_summary",
        "fields_read": ["projects[compiler].summary", "projects[compiler].stack"],
        "capability": "answer_from_record",
        "answer": "The compiler project is a course compiler.\nIt has a parser.",
        "tools_called": [{"name": "link_check:https://x", "ok": True, "latency_ms": 3}],
        "missing": ["deployment date"],
        "language": "en",
        "channel": "http",
        "latency_ms": 900,
    }
    assert format_trace(data) == (
        "Question: Summarize my compiler project.\n"
        "Intent: project_summary\n"
        "Fields read: projects[compiler].summary, projects[compiler].stack\n"
        "Capability: answer_from_record\n"
        "Tools: link_check:https://x (ok)\n"
        "Missing: deployment date\n"
        "Answer: The compiler project is a course compiler.\n"
        "        It has a parser."
    )


def test_format_trace_without_fields() -> None:
    text = format_trace(
        {
            "question": "q",
            "intent": "fact_lookup",
            "fields_read": [],
            "capability": "refuse_unpublished",
            "answer": "No.",
            "tools_called": [],
            "missing": [],
        }
    )
    assert "Fields read: (none)" in text
    assert "Tools" not in text and "Missing" not in text


def test_format_trace_strips_terminal_control_characters() -> None:
    text = format_trace(
        {
            "question": "hi\x1b[2J\x1b]0;pwned\x07 there‌یک",
            "intent": "fact_lookup",
            "fields_read": [],
            "capability": "clarify",
            "answer": "ok\x9b31m",
            "tools_called": [],
            "missing": [],
        }
    )
    assert "\x1b" not in text and "\x07" not in text and "\x9b" not in text
    assert "there‌یک" in text  # ZWNJ is meaningful in Persian and stays


def test_gap_table_strips_control_characters() -> None:
    from rich.console import Console

    from app.cli import gap_table

    console = Console(record=True, width=120)
    console.print(gap_table([(1, 1, "en", "evil\x1b[31m text", "2026-10-30")]))
    assert "\x1b[31m" not in console.export_text(styles=False)
