"""Fixed, localized replies for outcomes code decides (refusals, clarifications, greetings).

These never come from the model, so they can never contain an invented fact.
"""

from app.domain import Lang

_ACTION_NAMES: dict[str, dict[str, str]] = {
    "send_email": {"en": "send emails", "fa": "ایمیل بفرستم"},
    "book_meeting": {"en": "book meetings", "fa": "جلسه رزرو کنم"},
    "apply_to_job": {"en": "apply to jobs", "fa": "برای شغلی درخواست بدهم"},
    "speak_for_sharif": {"en": "speak for Sharif University", "fa": "از طرف دانشگاه شریف حرف بزنم"},
    "contact_third_party": {"en": "contact anyone", "fa": "با کسی تماس بگیرم"},
}

_TEMPLATES: dict[str, dict[str, str]] = {
    "refuse_action": {
        "en": "I can only answer questions about Moeein — I can't {action} on his behalf. "
        "His contact details are on this page if you'd like to reach him directly.",
        "fa": "من فقط به سؤال‌ها دربارهٔ معین پاسخ می‌دهم و نمی‌توانم از طرف او {action}. "
        "اگر می‌خواهید مستقیم با او در ارتباط باشید، اطلاعات تماسش در همین صفحه هست.",
    },
    "refuse_topic": {
        "en": "Moeein has chosen not to publish anything about {topic}, so I won't discuss it.",
        "fa": "معین تصمیم گرفته دربارهٔ «{topic}» چیزی منتشر نکند، پس دربارهٔ آن صحبت نمی‌کنم.",
    },
    "out_of_scope": {
        "en": "That's outside what this page covers. I only answer questions about Moeein — his "
        "projects, experience, courses, reading, and fit for a role.",
        "fa": "این سؤال خارج از موضوع این صفحه است. من فقط دربارهٔ معین پاسخ می‌دهم: پروژه‌ها، "
        "سوابق کاری، درس‌ها، مطالعه و تناسبش با یک موقعیت شغلی.",
    },
    "clarify_project": {
        "en": "Which project do you mean: {options}?",
        "fa": "منظورتان کدام پروژه است: {options}؟",
    },
    "clarify_project_examples": {
        "en": "Which project do you mean? For example: {options}.",
        "fa": "منظورتان کدام پروژه است؟ برای مثال: {options}.",
    },
    "clarify_entity": {
        "en": "Which one do you mean: {options}?",
        "fa": "منظورتان کدام مورد است: {options}؟",
    },
    "jobfit_summary": {
        "en": "Evidence coverage for {title}: {pct}% — {band}. "
        "{matched} of {total} requirements matched, {partial} partially, "
        "{missing} without evidence.",
        "fa": "پوشش شواهد برای {title}: {pct}٪ — {band}. "
        "از {total} شرط، {matched} مورد تطابق کامل، {partial} مورد تطابق نسبی و {missing} مورد "
        "بدون شاهد در رکورد.",
    },
    "smalltalk": {
        "en": "Hi! What would you like to know about Moeein — a project, his experience, "
        "or whether he fits a role?",
        "fa": "سلام! دربارهٔ معین چه می‌خواهید بدانید؟ یک پروژه، سوابق کاری، یا تناسبش با یک "
        "موقعیت شغلی؟",
    },
    "job_needed": {
        "en": "Which role should I check? Share the job link or paste the job description.",
        "fa": "تناسب با کدام موقعیت را بررسی کنم؟ لینک آگهی را بفرستید یا متن آن را وارد کنید.",
    },
}


VERDICT_NAMES: dict[str, dict[str, str]] = {
    "strong": {"en": "strong evidence of fit", "fa": "شواهد قوی برای تناسب"},
    "partial": {"en": "partial evidence of fit", "fa": "تناسب نسبی"},
    "weak": {"en": "weak evidence of fit", "fa": "شواهد ضعیف برای تناسب"},
}


def message(key: str, language: Lang, **values: str) -> str:
    return _TEMPLATES[key][language].format(**values)


def action_name(action: str, language: Lang) -> str:
    return _ACTION_NAMES.get(action, {}).get(language, action)


def join_options(options: list[str], language: Lang) -> str:
    if len(options) <= 1:
        return "".join(options)
    if language == "fa":
        return "، ".join(options[:-1]) + " یا " + options[-1]
    return ", ".join(options[:-1]) + " or " + options[-1]
