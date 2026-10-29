"""Starter questions: a curated set per audience and language, plus owner-approved FAQ."""

from app.domain import Audience, Lang
from app.record.schema import Record

FAQ_SUGGESTIONS = 2

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


async def suggestions(audience: Audience, lang: Lang, record: Record) -> list[str]:
    """Only text Moeein wrote or approved is shown: the curated set, plus his newest FAQ
    questions (added through ``me-agent gaps answer``). Raw visitor text is never echoed."""
    static = STATIC[audience][lang]
    newest = sorted(record.faq, key=lambda f: f.added, reverse=True)
    extra = [f.question for f in newest if f.question not in static][:FAQ_SUGGESTIONS]
    return [*static, *extra]
