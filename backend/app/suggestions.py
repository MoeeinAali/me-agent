"""Starter questions: a fixed set per audience and language, plus what visitors ask most."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TraceRow
from app.domain import Audience, Lang

POPULAR_DAYS = 30
POPULAR_COUNT = 2
# Visitor text is shown to other visitors only when many people asked it and it looks harmless.
POPULAR_MIN_CONVERSATIONS = 3
POPULAR_MAX_CHARS = 100
_UNSAFE = re.compile(r"https?://|www\.|@|<|>|\.(com|ir|net|org|io)\b", re.I)

STATIC: dict[str, dict[str, list[str]]] = {
    "recruiter": {
        "en": [
            "What has Moeein built at Yektanet?",
            "Summarize his strongest project.",
            "Does he fit a senior frontend role?",
            "Which languages does he speak?",
        ],
        "fa": [
            "معین در یکتانت چه چیزهایی ساخته است؟",
            "قوی‌ترین پروژه‌اش را خلاصه کن.",
            "آیا برای یک موقعیت فرانت‌اند ارشد مناسب است؟",
            "به چه زبان‌هایی مسلط است؟",
        ],
    },
    "tech_lead": {
        "en": [
            "How is Comeback architected?",
            "Has he worked on real-time systems?",
            "What does his Kubernetes and CI/CD experience look like?",
            "Which state-management tools does he use?",
        ],
        "fa": [
            "معماری پروژه کامبک چطور است؟",
            "تجربه کار با سیستم‌های بلادرنگ دارد؟",
            "تجربه‌اش با کوبرنتیز و CI/CD چیست؟",
            "از چه ابزارهای مدیریت state استفاده می‌کند؟",
        ],
    },
    "professor": {
        "en": [
            "Which courses has Moeein taken?",
            "Which courses has he been a TA for?",
            "What did his Database Design course cover?",
            "What should I read to follow his work?",
        ],
        "fa": [
            "معین چه درس‌هایی گذرانده است؟",
            "دستیار آموزشی کدام درس‌ها بوده است؟",
            "درس طراحی پایگاه داده‌اش چه سرفصل‌هایی داشت؟",
            "برای آشنایی با کارهایش چه بخوانم؟",
        ],
    },
    "general": {
        "en": [
            "Summarize the Comeback project.",
            "What books has he read?",
            "Tell me about his project.",
            "What can't this page do?",
        ],
        "fa": [
            "پروژه کامبک را خلاصه کن.",
            "چه کتاب‌هایی خوانده است؟",
            "درباره پروژه‌اش بگو.",
            "این صفحه چه کارهایی انجام نمی‌دهد؟",
        ],
    },
}


async def suggestions(audience: Audience, lang: Lang, session: AsyncSession) -> list[str]:
    since = datetime.now(UTC) - timedelta(days=POPULAR_DAYS)
    popular = await session.scalars(
        select(TraceRow.question)
        .where(
            TraceRow.created_at >= since,
            TraceRow.language == lang,
            TraceRow.channel != "eval",
            TraceRow.capability.in_(["answer_from_record", "answer_from_api"]),
        )
        .group_by(TraceRow.question)
        .having(func.count(distinct(TraceRow.conversation_id)) >= POPULAR_MIN_CONVERSATIONS)
        .order_by(func.count(distinct(TraceRow.conversation_id)).desc())
        .limit(POPULAR_COUNT * 5)
    )
    static = STATIC[audience][lang]
    extra = [
        q
        for q in popular
        if q not in static and len(q) <= POPULAR_MAX_CHARS and not _UNSAFE.search(q)
    ][:POPULAR_COUNT]
    return [*static, *extra]
