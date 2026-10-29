"""Minimal valid record payloads for tests."""

from typing import Any


def minimal_record() -> dict[str, Any]:
    return {
        "meta": {"version": "2026-10-29", "owner": "Moeein Aali", "sources": ["cv"]},
        "person": {
            "name": "Moeein Aali",
            "headline": "Full-Stack Software Engineer",
            "positioning": "Builds production systems end to end.",
            "about": ["Computer Engineering student at Sharif."],
            "location": "Tehran, Iran",
            "languages": [{"name": "Persian", "level": "Native"}],
        },
        "contact": {
            "email": "moeeeinaali@gmail.com",
            "phone": "+98 935 1090 753",
            "website": "https://moeein.me",
            "github": "https://github.com/moeeinaali",
            "linkedin": "https://linkedin.com/in/moeein",
        },
        "education": [],
        "honors": [],
        "courses_taken": [],
        "teaching": [],
        "experience": [],
        "projects": [
            {
                "id": "comeback",
                "title": "Comeback",
                "summary": "A Persian sports PWA.",
                "date": "2026-08",
                "tags": ["nextjs"],
                "tech": ["Next.js"],
                "links": {"live": "https://comeback.top"},
            }
        ],
        "service": [],
        "skills": [],
        "books": [],
        "faq": [],
        "limits": {
            "forbidden_actions": ["send_email"],
            "unpublished_topics": ["salary expectations"],
            "guardrails": ["Never state a fact absent from the record."],
        },
    }
