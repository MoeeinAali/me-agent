# hrcando adapter — live status (2026-10-29)

Endpoint: `GET https://careerapi.hrcando.ir/api/v1/CareerPage/GetCareerPageJobPageInfoByJobGuid/{uuid}`
with headers `careerauthkey`, `address` (the original job URL), `origin`/`referer`
(`https://career.hrcando.ir`), `accept: application/json, text/plain, */*`.

| Link | Result |
|---|---|
| `career.hrcando.ir/co/Milli/job-detail/6867af3e-…` | ✅ 200, mapped correctly |
| `jobs.bitpin.org/job-detail/076fb0c1-…` (company domain) | ❌ 500 with either origin |

The `careerauthkey` is not in the career-page JS bundle, so it is most likely issued per
career site at runtime; the configured key (`HRCANDO_CAREER_AUTH_KEY`) works for
`career.hrcando.ir/co/*` pages. Company-domain pages fall back to: "paste the job description".
To support them, capture the `careerauthkey` a browser sends on that domain and add per-host keys.
