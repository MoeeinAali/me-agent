import type { Audience, Capability, Lang } from "./api/types";

export const CAPABILITY_LABELS: Record<Capability, Record<Lang, string>> = {
  answer_from_record: { en: "From record", fa: "از رکورد" },
  answer_from_api: { en: "From API", fa: "از API" },
  clarify: { en: "Needs clarification", fa: "نیاز به توضیح" },
  refuse_unpublished: { en: "Not published", fa: "منتشر نشده" },
  refuse_action: { en: "Not allowed", fa: "مجاز نیست" },
  out_of_scope: { en: "Outside this page", fa: "خارج از این صفحه" },
};

/** What the action means for the visitor, in one plain sentence. */
export const CAPABILITY_EXPLAINED: Record<Capability, Record<Lang, string>> = {
  answer_from_record: {
    en: "Every sentence is backed by Moeein's published record.",
    fa: "هر جمله با رکورد منتشرشده‌ی معین پشتیبانی می‌شود.",
  },
  answer_from_api: {
    en: "Backed by the record plus a live check (GitHub, a project's site, or the job page).",
    fa: "با رکورد و یک بررسی زنده (گیت‌هاب، سایت پروژه یا آگهی شغلی) پشتیبانی می‌شود.",
  },
  clarify: { en: "The question could mean several things, so the agent asked first.", fa: "سؤال چند معنا داشت، پس دستیار اول پرسید." },
  refuse_unpublished: {
    en: "Moeein hasn't published this, so the agent won't guess.",
    fa: "معین این را منتشر نکرده، پس دستیار حدس نمی‌زند.",
  },
  refuse_action: { en: "The agent can only answer questions, not act for Moeein.", fa: "دستیار فقط جواب می‌دهد و از طرف معین کاری انجام نمی‌دهد." },
  out_of_scope: { en: "This page only answers questions about Moeein.", fa: "این صفحه فقط درباره‌ی معین جواب می‌دهد." },
};

export const AUDIENCE_LABELS: Record<Audience, Record<Lang, string>> = {
  recruiter: { en: "Recruiter", fa: "استخدام‌کننده" },
  tech_lead: { en: "Tech lead or CTO", fa: "مدیر فنی" },
  professor: { en: "Professor", fa: "استاد" },
  general: { en: "Just curious", fa: "کنجکاو" },
};

const STRINGS = {
  title: { en: "Ask Moeein's agent", fa: "از دستیار معین بپرسید" },
  name: { en: "Moeein Aali", fa: "معین عالی" },
  role: { en: "Full-stack software engineer", fa: "مهندس نرم‌افزار فول‌استک" },
  intro: {
    en: "Ask about his projects, experience, courses, or whether he fits a role. Answers come only from his published record, and every sentence links to its source.",
    fa: "درباره‌ی پروژه‌ها، تجربه، درس‌ها یا تناسبش با یک شغل بپرسید. پاسخ‌ها فقط از رکورد منتشرشده‌ی او می‌آیند و هر جمله به منبعش لینک دارد.",
  },
  whoAsking: { en: "Who's asking?", fa: "شما کی هستید؟" },
  whoAskingHint: { en: "Answers are framed for you; the facts stay the same.", fa: "پاسخ‌ها برای شما تنظیم می‌شوند؛ واقعیت‌ها همان می‌مانند." },
  tryAsking: { en: "Try asking", fa: "مثلاً بپرسید" },
  jobCardTitle: { en: "Check fit for a job", fa: "بررسی تناسب با یک شغل" },
  jobCardBody: {
    en: "Paste a job link, its text, or a PDF. You get a requirement-by-requirement scorecard with proof.",
    fa: "لینک، متن یا PDF آگهی را بدهید تا جدول تطبیق نیازمندی‌ها را با مدرک ببینید.",
  },
  placeholder: { en: "Ask about Moeein's projects, experience, courses…", fa: "درباره‌ی پروژه‌ها، تجربه و درس‌های معین بپرسید…" },
  send: { en: "Send", fa: "ارسال" },
  newChat: { en: "New conversation", fa: "گفتگوی تازه" },
  footer: {
    en: "Answers come only from Moeein's record, GitHub, and job pages you share. Powered by GapGPT.",
    fa: "پاسخ‌ها فقط از رکورد معین، گیت‌هاب و آگهی‌هایی که می‌فرستید می‌آیند. با GapGPT.",
  },
  limits: { en: "What I can't do", fa: "محدودیت‌ها" },
  limitsIntro: {
    en: "The same list the agent is instructed with. Anything here gets a polite refusal.",
    fa: "همان فهرستی که دستیار با آن تنظیم شده. هر درخواستی از این دست مؤدبانه رد می‌شود.",
  },
  forbidden: { en: "Actions it won't take", fa: "کارهایی که انجام نمی‌دهد" },
  unpublished: { en: "Topics Moeein didn't publish", fa: "موضوع‌های منتشرنشده" },
  guardrails: { en: "Rules it follows", fa: "قواعدی که رعایت می‌کند" },
  limitsFailed: { en: "Couldn't load the list. Check your connection and reopen this panel.", fa: "فهرست بارگیری نشد. اتصال را بررسی کنید و دوباره باز کنید." },
  why: { en: "Why this answer", fa: "چرا این جواب" },
  sources: { en: "Sources", fa: "منابع" },
  noSources: { en: "This reply cites no sources: it's a fixed response, not a claim about Moeein.", fa: "این پاسخ منبعی ندارد: پاسخ ثابت است، نه ادعایی درباره‌ی معین." },
  inspectorEmpty: {
    en: "Ask something, and this panel shows where each sentence of the answer came from.",
    fa: "چیزی بپرسید تا این بخش نشان دهد هر جمله‌ی پاسخ از کجا آمده.",
  },
  progress: { en: "How it answered", fa: "مراحل پاسخ" },
  details: { en: "Technical details", fa: "جزئیات فنی" },
  intent: { en: "Intent", fa: "هدف" },
  capability: { en: "Action", fa: "اقدام" },
  fields: { en: "Record fields read", fa: "فیلدهای خوانده‌شده" },
  tools: { en: "Live checks", fa: "بررسی‌های زنده" },
  missing: { en: "Not in the record", fa: "در رکورد نیست" },
  none: { en: "None", fa: "هیچ" },
  retry: { en: "Try again", fa: "تلاش دوباره" },
  copy: { en: "Copy answer", fa: "کپی پاسخ" },
  copied: { en: "Answer copied", fa: "پاسخ کپی شد" },
  attachJob: { en: "Check fit for a job", fa: "بررسی تناسب با یک شغل" },
  attachJobHint: {
    en: "Links from career.hrcando.ir are read directly. For any other site, paste the text or upload the PDF.",
    fa: "لینک‌های career.hrcando.ir مستقیم خوانده می‌شوند. برای سایت‌های دیگر متن یا PDF را بدهید.",
  },
  jobUrl: { en: "Link", fa: "لینک" },
  jobText: { en: "Paste text", fa: "متن آگهی" },
  jobPdf: { en: "PDF", fa: "PDF" },
  jobUrlInput: { en: "Job posting link", fa: "لینک آگهی" },
  jobTextInput: { en: "Job posting text", fa: "متن آگهی شغلی" },
  jobPdfInput: { en: "Job posting PDF", fa: "فایل PDF آگهی" },
  check: { en: "Check fit", fa: "بررسی" },
  pdfTooBig: { en: "The PDF must be 2 MB or smaller.", fa: "حجم PDF باید حداکثر ۲ مگابایت باشد." },
  coverage: { en: "Coverage", fa: "پوشش" },
  speak: { en: "Read answers aloud", fa: "خواندن پاسخ‌ها" },
  micUnsupported: { en: "Voice input isn't supported in this browser.", fa: "این مرورگر ورودی صوتی را پشتیبانی نمی‌کند." },
  micDenied: { en: "Microphone access was denied. Allow it in your browser's site settings to ask by voice.", fa: "دسترسی به میکروفون داده نشد. برای پرسش صوتی آن را در تنظیمات مرورگر مجاز کنید." },
  record: { en: "Ask by voice (up to 60 s)", fa: "پرسیدن با صدا (تا ۶۰ ثانیه)" },
  stop: { en: "Stop and send", fa: "توقف و ارسال" },
  voiceQuestion: { en: "(voice question)", fa: "(پرسش صوتی)" },
  jobQuestion: { en: "How well does Moeein fit this job?", fa: "معین چقدر برای این شغل مناسب است؟" },
  offline: { en: "The agent is offline right now", fa: "دستیار الان در دسترس نیست" },
  offlineBody: {
    en: "Questions may fail until it's back. Moeein's site and CV are at moeein.me.",
    fa: "تا برگشتن آن ممکن است پرسش‌ها ناموفق باشند. سایت و رزومه‌ی معین در moeein.me است.",
  },
  enterHint: { en: "to send", fa: "برای ارسال" },
  shiftEnterHint: { en: "new line", fa: "خط جدید" },
  language: { en: "فارسی", fa: "English" },
  thinking: { en: "Reading the record", fa: "در حال خواندن رکورد" },
} satisfies Record<string, Record<Lang, string>>;

export type StringKey = keyof typeof STRINGS;
export const t = (key: StringKey, lang: Lang) => STRINGS[key][lang];

export const STAGE_LABELS: Record<string, Record<Lang, string>> = {
  understand: { en: "Understood the question", fa: "فهم سؤال" },
  resolve: { en: "Matched what it refers to", fa: "یافتن موضوع سؤال" },
  policy: { en: "Checked the limits", fa: "بررسی محدودیت‌ها" },
  evidence: { en: "Gathered evidence", fa: "جمع‌آوری شواهد" },
  generate: { en: "Wrote the answer", fa: "نوشتن پاسخ" },
  verify: { en: "Verified every claim", fa: "راستی‌آزمایی ادعاها" },
};
