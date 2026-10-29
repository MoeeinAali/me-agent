"""Step ③: what the page refuses, decided in code before any answer is generated."""

import math
import re
from dataclasses import dataclass

from app.domain import Capability
from app.llm.client import LLM
from app.pipeline.understand import Understanding
from app.record.schema import Record

TOPIC_SIMILARITY = 0.78

# Keyword rules for the unpublished topics, in both languages. They back up the embedding match,
# which can miss short or colloquial phrasings.
_TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "salary expectations": re.compile(
        r"salary|compensation|expected pay|how much .* (paid|earn)|حقوق|دستمزد|درآمد", re.I
    ),
    "home address": re.compile(
        r"home address|where does he live|آدرس\s*(منزل|خانه|خونه)|کجا\s*زندگی", re.I
    ),
    "political views": re.compile(r"politic|سیاس", re.I),
    "religious views": re.compile(r"religio|مذهب|\bدین\b", re.I),
    "family": re.compile(r"married|wife|girlfriend|\bfamily\b|ازدواج|همسر|متاهل|خانواده", re.I),
    "health": re.compile(r"\bhealth\b|illness|disease|بیماری|سلامت", re.I),
}


@dataclass(frozen=True)
class PolicyDecision:
    capability: Capability | None
    reason: str | None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


async def policy(llm: LLM, u: Understanding, record: Record) -> PolicyDecision:
    limits = record.limits
    if u.wants_action and u.wants_action in limits.forbidden_actions:
        return PolicyDecision("refuse_action", u.wants_action)
    if u.intent == "out_of_scope":
        return PolicyDecision("out_of_scope", None)

    text = f"{u.message}\n{u.asks_for}"
    for topic in limits.unpublished_topics:
        pattern = _TOPIC_PATTERNS.get(topic)
        if pattern and pattern.search(text):
            return PolicyDecision("refuse_unpublished", topic)

    if limits.unpublished_topics and u.asks_for:
        vectors = await llm.embed([u.asks_for, *limits.unpublished_topics])
        asked, topics = vectors[0], vectors[1:]
        best = max(range(len(topics)), key=lambda i: _cosine(asked, topics[i]))
        if _cosine(asked, topics[best]) >= TOPIC_SIMILARITY:
            return PolicyDecision("refuse_unpublished", limits.unpublished_topics[best])
    return PolicyDecision(None, None)
