import type { Capability, Lang } from "./api/types";

export const CAPABILITY_LABELS: Record<Capability, Record<Lang, string>> = {
  answer_from_record: { en: "From record", fa: "از رکورد" },
  answer_from_api: { en: "From API", fa: "از API" },
  clarify: { en: "Needs clarification", fa: "نیاز به توضیح" },
  refuse_unpublished: { en: "Not published", fa: "منتشر نشده" },
  refuse_action: { en: "Not allowed", fa: "مجاز نیست" },
  out_of_scope: { en: "Outside this page", fa: "خارج از این صفحه" },
};

const STRINGS = {
  headline: {
    en: "An interview agent that answers only from Moeein's record, and shows why.",
    fa: "دستیار مصاحبه‌ای که فقط از رکورد معین جواب می‌دهد و دلیلش را نشان می‌دهد.",
  },
  placeholder: { en: "Ask about Moeein's projects, experience, courses…", fa: "درباره‌ی پروژه‌ها، تجربه و درس‌های معین بپرسید…" },
  send: { en: "Send", fa: "ارسال" },
  footer: {
    en: "Answers come only from Moeein's record, GitHub, and job pages you share. Powered by GapGPT.",
    fa: "پاسخ‌ها فقط از رکورد معین، گیت‌هاب و آگهی‌های شغلی‌ای که شما می‌فرستید می‌آیند. با GapGPT.",
  },
  limits: { en: "What I can't do", fa: "محدودیت‌ها" },
  forbidden: { en: "Actions I won't take", fa: "کارهایی که انجام نمی‌دهم" },
  unpublished: { en: "Topics Moeein didn't publish", fa: "موضوع‌های منتشرنشده" },
  guardrails: { en: "Guardrails", fa: "قواعد" },
  why: { en: "Why this answer", fa: "چرا این جواب" },
  intent: { en: "Intent", fa: "هدف" },
  capability: { en: "Action", fa: "اقدام" },
  fields: { en: "Fields read", fa: "فیلدهای خوانده‌شده" },
  tools: { en: "Tools called", fa: "ابزارها" },
  missing: { en: "Missing facts", fa: "اطلاعات ناموجود" },
  none: { en: "none", fa: "هیچ" },
  retry: { en: "Retry", fa: "تلاش دوباره" },
  attachJob: { en: "Check fit for a job", fa: "بررسی تناسب با یک شغل" },
  jobUrl: { en: "Link", fa: "لینک" },
  jobText: { en: "Paste text", fa: "متن آگهی" },
  jobPdf: { en: "PDF", fa: "PDF" },
  jobUrlInput: { en: "Job posting link", fa: "لینک آگهی" },
  jobTextInput: { en: "Job posting text", fa: "متن آگهی شغلی" },
  jobPdfInput: { en: "Job posting PDF", fa: "فایل PDF آگهی" },
  check: { en: "Check fit", fa: "بررسی" },
  pdfTooBig: { en: "The PDF must be 2 MB or smaller.", fa: "حجم PDF باید حداکثر ۲ مگابایت باشد." },
  coverage: { en: "Coverage", fa: "پوشش" },
  speak: { en: "Speak answers", fa: "خواندن پاسخ‌ها" },
  micUnsupported: { en: "Voice input isn't supported in this browser.", fa: "این مرورگر ورودی صوتی را پشتیبانی نمی‌کند." },
  micDenied: { en: "Microphone access was denied.", fa: "دسترسی به میکروفون داده نشد." },
  record: { en: "Ask by voice", fa: "پرسیدن با صدا" },
  stop: { en: "Stop recording", fa: "توقف ضبط" },
  voiceQuestion: { en: "(voice question)", fa: "(پرسش صوتی)" },
  jobQuestion: { en: "How well does Moeein fit this job?", fa: "معین چقدر برای این شغل مناسب است؟" },
} satisfies Record<string, Record<Lang, string>>;

export type StringKey = keyof typeof STRINGS;
export const t = (key: StringKey, lang: Lang) => STRINGS[key][lang];
