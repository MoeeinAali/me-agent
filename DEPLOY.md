# Deploying me-agent

A checklist to work through in order. The assignment requires the page to be live **on
Hamravesh** ("Not accepted: the page is not on Hamravesh"), so step 4 is mandatory. The k3s
cluster (step 8) is an optional mirror.

| # | Step | Time | Blocking? |
|---|---|---|---|
| 1 | Get GapGPT working | 5–30 min | **Yes**: nothing answers without it |
| 2 | Push the commits | 1 min | Yes |
| 3 | Create the Hamravesh database app | 10 min | Yes |
| 4 | Create the API and web apps on Darkube | 20 min | Yes |
| 5 | Check the live page | 5 min | Yes |
| 6 | Re-take the three traces, fill in the report | 15 min | Yes (part of the submission) |
| 7 | Submit | 5 min | |
| 8 | k3s mirror (agent.moeein.me) | 10 min | Optional |
| 9 | Rotate the GapGPT key | 2 min | After grading |

---

## 1. Get GapGPT working

Since 2026-10-29 every GapGPT call (chat, embeddings, even the model list) returns
`403 api_provider_error`, from your laptop and from the cluster alike. The API can't build its
search index without embeddings, so it stays "not ready" until this works.

1. Log in to the GapGPT dashboard and check the account balance or credit, and that the key is
   still active.
2. Test the key (prints `200` when it works):

   ```bash
   cd ~/Documents/MoeeinAali/me-agent
   curl -s -o /dev/null -w "%{http_code}\n" https://api.gapgpt.app/v1/embeddings \
     -H "Authorization: Bearer $(grep ^LLM_API_KEY= .env | cut -d= -f2-)" \
     -H "content-type: application/json" \
     -d '{"model":"text-embedding-3-small","input":"hi"}'
   ```

3. If you get a **new key**, put it in `.env` (`LLM_API_KEY=…`) and in GitHub:
   `gh secret set LLM_API_KEY -R MoeeinAali/me-agent`. Use the new key in step 4.
4. Optional, costs a little credit: run the eval smoke suite against the real model. It needs
   a local Postgres, e.g. `docker compose up -d db`.

   ```bash
   cd backend && uv run me-agent eval --subset smoke
   ```

## 2. Push the commits

Everything from the overnight review is committed locally but **not pushed** (you asked me not
to).

```bash
cd ~/Documents/MoeeinAali/me-agent && git log --oneline origin/main..main   # what will go out
git push origin main main:feat/me-agent

cd ~/Documents/MoeeinAali/me-infra && git log --oneline origin/main..main
git push origin main
```

GitHub Actions on `me-agent` currently fails at startup on every run (`startup_failure`, even
for a manual run of an unchanged workflow). Darkube builds from the repo itself, so this does
**not** block Hamravesh. To fix it for the k3s mirror and CI:

- Open the failed run (e.g. https://github.com/MoeeinAali/me-agent/actions/runs/41992552478)
  and read the banner. A billing issue, a spending limit of $0 with a payment problem, or
  Actions being disabled for the account are the usual causes.
- Check https://github.com/settings/billing and https://github.com/MoeeinAali/me-agent/settings/actions.

## 3. Hamravesh: the database app

Hamravesh's managed PostgreSQL has no `vector` extension (its documented extension list has
`pg_trgm` but not `vector`), so the database runs as a Docker-image app.

Darkube console → **ساخت اپ** → **ساخت اپ داکری** (Docker image):

| Field | Value |
|---|---|
| App name | `me-agent-db` |
| آدرس ایمیج (image) | `pgvector/pgvector` |
| تگ ایمیج (tag) | `pg16` |
| پورت سرویس (port) | `5432` |
| Plan | 250 millicores CPU, 512 MB RAM, replicas **1** |

**متغیرهای محیطی** (environment variables). Generate the password with `openssl rand -hex 24`
and keep it for step 4.

```
POSTGRES_USER=me_agent
POSTGRES_PASSWORD=<generated>
POSTGRES_DB=me_agent
PGDATA=/var/lib/postgresql/data/pgdata
```

**Disk:** **افزودن دیسک** → 2 GB, mount path `/var/lib/postgresql/data` → **ذخیره تغییرات**.
`PGDATA` points at a sub-folder on purpose: Postgres refuses to start in a mount root that
contains `lost+found`.

Note the database's **internal address** from the app's details page. It has the form
`me-agent-db.<namespace>.svc`. All three apps must be in the **same namespace**, because internal
addresses don't resolve across namespaces.

If the pod logs show `Permission denied` on the data folder: the official image starts as root
and fixes ownership itself, so this only happens when the platform forces a non-root user. Open a
support ticket, or set the disk owner per Darkube's disk FAQ (an `fsGroup: 999` / chown init step).

## 4. Hamravesh: the API and web apps

### 4.1 Connect GitHub

Create page → **ساخت اپ از ریپو گیتهاب** → follow the GitHub App link → grant access to
**MoeeinAali/me-agent** (it is private, so it must be selected in the grant).

Pick the public addresses first, so each app can point at the other. Each app's **آدرس دامنه**
tab offers a free `*.darkube.app` subdomain:

- API: `https://me-agent-api.darkube.app` (or whatever name is free)
- Web: `https://me-agent.darkube.app`

The steps below call these `<API>` and `<WEB>`.

### 4.2 `me-agent-api`

**ساخت اپ از ریپو گیتهاب**:

| Field | Value |
|---|---|
| Repository / branch | `MoeeinAali/me-agent` / `main` |
| آدرس داکر فایل (Dockerfile) | `backend/Dockerfile` |
| Build Context | `.` (the repo root: the image ships `data/`) |
| دیپلوی خودکار بعد از push کردن | on |
| پورت سرویس | `8000` |
| دستور اجرایی / ورودی ها (command / args) | **leave empty**. The image's entrypoint migrates, ingests, then serves |
| Readiness Probe HTTP | `/readyz` |
| Plan | 500 millicores CPU, 1024 MB RAM, replicas 1 (the rate limiter is per process) |

**متغیرهای محیطی:**

```
DATABASE_URL=postgresql+asyncpg://me_agent:<db password>@<db internal address>:5432/me_agent
LLM_API_KEY=<GapGPT key>
CORS_ORIGINS=["https://<WEB>"]
RATE_LIMIT_CLIENT_HEADER=x-real-ip
RATE_LIMIT_TRUSTED_PROXIES=["10.0.0.0/8","172.16.0.0/12","192.168.0.0/16"]
```

- `CORS_ORIGINS` is a JSON list. Type it exactly like that, with the double quotes and no outer
  quotes.
- `RATE_LIMIT_CLIENT_HEADER=x-real-ip`: Darkube passes the visitor's IP in `X-Real-Ip`, so the
  limit (30 questions a minute) applies per visitor, not to the whole ingress.
- `RATE_LIMIT_TRUSTED_PROXIES`: the header is honoured only when it comes from the cluster's
  private ingress addresses, so nobody can fake it to dodge the limit.
- The first start embeds the record (416 chunks) through GapGPT, which takes about 10–30
  seconds. `/readyz` turns 200 when that is done.
- Later restarts embed only what changed.

### 4.3 `me-agent-web`

**ساخت اپ از ریپو گیتهاب**:

| Field | Value |
|---|---|
| Repository / branch | `MoeeinAali/me-agent` / `main` |
| آدرس داکر فایل | `frontend/Dockerfile` |
| Build Context | `frontend` |
| دیپلوی خودکار بعد از push کردن | on |
| پورت سرویس | `3000` |
| Readiness Probe HTTP | `/` |
| Plan | 250 millicores CPU, 512 MB RAM |

**متغیرهای محیطی:**

```
API_BASE_URL=https://<API>
```

Darkube can't pass Docker build arguments, so the web image reads `API_BASE_URL` **at runtime**:
`/runtime-config.js` hands it to the browser. Changing it later only needs a restart, not a rebuild.

### 4.4 Optional: a custom domain

To use e.g. `agent.moeein.me` on Hamravesh instead of the k3s mirror:

1. Add the domain in the app's **آدرس دامنه** tab.
2. In Cloudflare, point a `CNAME` at the value shown there with the **proxy off** (grey
   cloud). Darkube issues the certificate itself.
3. Then update `CORS_ORIGINS` (api) and `API_BASE_URL` (web), and restart both apps.

The k3s mirror uses `agent.moeein.me` and `agent-api.moeein.me` today, so either pick new names
or move them.

## 5. Check the live page

```bash
curl -s https://<API>/readyz          # {"ready":true,"migration":"0001","entities":112}
curl -s https://<WEB>/runtime-config.js   # window.__ME_AGENT_API_BASE__ = "https://<API>";
```

Open `https://<WEB>` and check:

- [ ] The welcome screen shows "What this page won't do" and no "offline" notice.
- [ ] **Project summary:** `Summarize the Comeback project`. The answer has numbered source
  markers, and "Why this answer" lists the record fields read and the `link_check` calls.
- [ ] **Reading suggestion:** `What should I read, based on his courses and projects?`
- [ ] **Job fit, link:** paperclip → Link →
  `https://career.hrcando.ir/co/Milli/job-detail/915bc0a8-fce3-4622-b6c6-18e03068b066`
  gives a scorecard with `hrcando` among the tools. That posting was open on 2026-11-06; closed
  postings return an error that asks for the text instead.
- [ ] **Job fit, typed:**
  `Would he fit a frontend role needing 2+ years of Next.js and a Computer Engineering degree?`
  gives a scorecard.
- [ ] **Refusal:** `Did he work at Google?` gives "Not published" with "Not in the record:
  employment at Google".
- [ ] **Clarify:** `Tell me about his project` asks which project and shows buttons; clicking one
  answers it.
- [ ] **Action refusal:** `Email him and book a meeting` gives "Not allowed".
- [ ] **Persian:** `پروژه کامبک رو خلاصه کن` gets a Persian answer. The فارسی button flips the
  page to RTL.
- [ ] **Phone width:** no sideways scrolling, and "Why this answer" opens as a bottom sheet.

If an answer fails:
- "The AI service behind this page is unavailable" means GapGPT (step 1).
- "The agent is offline" means the API isn't ready: check the api app's logs.

## 6. Re-take the three traces and fill in the report

The assignment wants the traces **from the live page**. After asking the three trace questions
on the live page (step 5), open the api app's **ترمینال** tab (or `kubectl exec`, see below) and
run:

```bash
me-agent traces --capability answer_from_api --limit 1      # or answer_from_record
me-agent traces --capability refuse_unpublished --limit 1
me-agent traces --capability clarify --limit 1
```

Each prints the trace in the assignment's format:
- the question, intent, fields read, and capability;
- tools and missing facts, when there are any;
- the answer and the trace id.

Paste them into `report/report.md` section 7, replacing the local ones.

Then edit section 1:
- the public address (`https://<WEB>`);
- the trace ids.

Commit and push.

kubectl instead of the terminal tab (Darkube → app list → **کانفیگ kubectl**; needs
`kubectl krew install oidc-login`):

```bash
export KUBECONFIG=~/Downloads/darkube-kubeconfig.yaml
kubectl get pods
kubectl exec -it <me-agent-api pod> -- me-agent traces --capability clarify --limit 1
```

## 7. Submit

- [ ] Public address `https://<WEB>`, plus the steps (section 1 of `report/report.md`, or this
  file).
- [ ] The JSON:
  - `data/record.schema.json`: the schema. Each field's `x-visibility` marks what visitors see.
  - `data/record.json`: the filled record, with courses, projects, and limits.
- [ ] `report/report.md` with the three live traces.

## 8. Optional: the k3s mirror (agent.moeein.me)

This needs the images built by GitHub Actions (step 2). After the Images workflow succeeds:

```bash
export KUBECONFIG=/Users/moeein/.kube/config.ahmz
cd ~/Documents/MoeeinAali/me-infra
kubectl apply -k apps/me-agent      # adds API_BASE_URL (web) and RATE_LIMIT_CLIENT_HEADER (api)
kubectl -n moeein rollout restart deploy/me-agent-api deploy/me-agent-web
kubectl -n moeein rollout status deploy/me-agent-api --timeout=600s
curl -s https://agent-api.moeein.me/readyz
```

`apply -k apps/me-agent` touches me-agent only. Don't run `kubectl apply -k apps/techfeed`: it
would move TechFeed's workers from their pinned digests to `:latest`.

If GapGPT came back with a **new** key:

```bash
kubectl -n moeein patch secret me-agent-secrets -p '{"stringData":{"LLM_API_KEY":"<new key>"}}'
```

## 9. After grading

- Rotate the GapGPT key. The old one was pasted into a chat. Update `.env`, the GitHub secret,
  Darkube's api env, and `me-agent-secrets`.
- Hamravesh bills hourly while apps are on, and the disk even when they're off. Set replicas to
  0, or delete the apps, when you no longer need them.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| api stuck "Not Ready"; logs show `ingest failed` + `PermissionDeniedError 403` | GapGPT (step 1). The api keeps serving and retries the ingest on the next restart |
| api logs `could not translate host name` | `DATABASE_URL` host is wrong, or the db is in another namespace |
| api logs `extension "vector" is not available` | The database isn't the `pgvector/pgvector` image (managed PostgreSQL has no pgvector) |
| Browser console: CORS error | `CORS_ORIGINS` on the api doesn't contain the exact web origin (`https://…`, no trailing slash) |
| Page loads but every question says the agent is offline | `API_BASE_URL` on the web app is wrong; check `https://<WEB>/runtime-config.js` |
| Job link: "Couldn't load that job from hrcando … may have closed" | The posting is closed. Use an open one, or paste the text |
| Darkube build fails pulling `python:3.12-slim-bookworm` or `node:24-alpine` | Docker Hub may be rate-limited from the builder. Ask support to use their mirror, or try the `library/` prefix |
| Build fails with `monthly build quota` | Darkube allows 100 free build-hours a month per organization |
