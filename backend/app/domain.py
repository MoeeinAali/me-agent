"""The API contract: what the agent returns and how it explains itself.

The frontend mirrors these names exactly (see ``data/api.schema.json``).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.config import get_settings

Capability = Literal[
    "answer_from_record",
    "answer_from_api",
    "clarify",
    "refuse_unpublished",
    "refuse_action",
    "out_of_scope",
]
Intent = Literal[
    "project_summary", "reading_suggestion", "job_fit", "fact_lookup", "out_of_scope", "smalltalk"
]
Audience = Literal["recruiter", "tech_lead", "professor", "general"]
Lang = Literal["fa", "en"]
Channel = Literal["http", "sse", "voice", "mcp", "eval"]
EvidenceSource = Literal["record", "github", "hrcando", "job_text", "link_check"]


class Proof(BaseModel):
    """How a visitor can check an evidence item themselves."""

    type: Literal["record", "github_repo", "github_commit", "live_url", "syllabus"]
    url: str | None = None
    status: Literal["up", "down", "unknown"] | None = None
    checked_at: datetime | None = None


class Evidence(BaseModel):
    id: str = Field(description="E1, E2, … — the handle claims cite")
    path: str = Field(description="Where the value came from, e.g. projects[comeback].tech")
    value: str
    source: EvidenceSource
    trusted: bool = Field(description="False for job text and READMEs: never evidence about Moeein")
    proof: Proof


class Claim(BaseModel):
    text: str
    evidence: list[str]


class ToolCall(BaseModel):
    name: str
    ok: bool
    latency_ms: int
    detail: str | None = None


class ScorecardRow(BaseModel):
    requirement: str
    category: Literal["must", "nice"]
    kind: Literal["skill", "experience", "education", "language", "other"]
    status: Literal["matched", "partial", "no_evidence"]
    evidence: list[str]


class JobSummary(BaseModel):
    source: str
    url: str | None = None
    company: str | None = None
    title: str | None = None


class Scorecard(BaseModel):
    job: JobSummary
    rows: list[ScorecardRow]
    coverage: float
    verdict: Literal["strong", "partial", "weak"]


class Trace(BaseModel):
    id: UUID
    question: str
    language: Lang
    intent: Intent
    audience: Audience
    channel: Channel
    fields_read: list[str]
    tools_called: list[ToolCall]
    capability: Capability
    answer: str
    missing: list[str]
    latency_ms: int
    tokens_in: int
    tokens_out: int
    prompt_version: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None
    audience: Audience = "general"
    job_url: HttpUrl | None = None
    job_text: str | None = None

    @field_validator("message")
    @classmethod
    def _message_bounds(cls, value: str) -> str:
        value = value.strip()
        limit = get_settings().max_message_chars
        if not value:
            raise ValueError("message must not be empty")
        if len(value) > limit:
            raise ValueError(f"message must be at most {limit} characters")
        return value

    @field_validator("job_text")
    @classmethod
    def _job_text_bounds(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        limit = get_settings().max_job_chars
        if len(value) > limit:
            raise ValueError(f"job_text must be at most {limit} characters")
        return value or None


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    capability: Capability
    claims: list[Claim]
    evidence: list[Evidence]
    scorecard: Scorecard | None = None
    clarify_options: list[str] | None = None
    transcript: str | None = None
    audio_b64: str | None = None
    trace: Trace
