# NDE Community Crawler — Weekly Run

You are running the weekly NDE Community Crawler. Your mission is to discover community forum posts where researchers are asking questions that the NIAID Data Ecosystem (NDE) could help answer, draft replies, and surface them for human review via GitHub Issues.

**NDE** (data.niaid.nih.gov) aggregates and integrates dataset metadata for infectious and immune-related diseases, enabling unified search across repositories including NCBI, ImmPort, ClinicalTrials.gov, and dozens more.

**Working directory:** /home/asu/Science/NDE-community-crawler

---

## Step 1 — Load memory and config

Read all four files before doing anything else:
- `config/forums.json` — approved forums to crawl, pending forums awaiting review, blocked forums
- `memory/seen_posts.json` — posts already surfaced (never re-surface these)
- `memory/thread_registry.json` — threads being tracked for followup activity
- `memory/run_log.json` — history of past runs (use to determine date range for this run)

---

## Step 2 — Crawl approved forums

For each forum in `config.approved`, search for posts from the **last 7 days** relevant to any of:
- Finding or accessing datasets for infectious diseases, pathogens, or immune-related conditions
- Searching across multiple biomedical data repositories
- NIAID-funded or NIH-funded research data access
- Dataset discovery and metadata in bioinformatics
- Multi-omics or clinical data integration for infectious/immune disease research

### Fetching pages: which tool to use

Some forums (Biostars, SEQanswers) sit behind a **Cloudflare JavaScript challenge** — plain `WebFetch`/`curl` get a 403 "Just a moment..." page. For those, use the Cloudflare-aware fetcher instead:

```bash
$NDE_PYTHON $NDE_FETCH "<url>" --text   # rendered text (default)
$NDE_PYTHON $NDE_FETCH "<url>" --html   # raw HTML when you need structure
```

(If `$NDE_PYTHON`/`$NDE_FETCH` are unset, use `.venv/bin/python agent/fetch.py`. The script must run under a virtual display; `run.sh` already wraps the whole run in `xvfb-run`.)

The fetcher exit codes matter:
- **0** — success, content on stdout
- **2** — Cloudflare *escalated* to an interactive challenge (usually from too many rapid requests). Stop hitting that forum this run and use the WebSearch fallback below.
- **3** — navigation error/timeout — retry once, then skip.

**Pacing (important):** Cloudflare escalates under bursts. Between requests to the SAME Cloudflare-protected forum, wait ~5–10 seconds (`sleep 7`) and keep total requests per forum modest (≤ ~15/run). For `candidate` posts you'll fetch full threads; for everything else prefer one listing/search page over many page fetches.

**Per-forum crawl strategy:**

- **Biostars** (Cloudflare) — Use the fetcher against the **JSON API** (cleaner + fewer requests than scraping):
  - Recent post IDs for a date: `https://www.biostars.org/api/stats/date/YYYY/MM/DD/` (returns `new_posts` ID list)
  - Post detail: `https://www.biostars.org/api/post/<id>/`
  - Fetch with `$NDE_FETCH "<api-url>" --text` and parse the JSON from stdout.
  - Pace with `sleep 7` between calls. **If you get exit code 2 (escalated), immediately switch to the fallback:** `WebSearch` for `site:biostars.org infectious disease dataset` (and similar queries) to surface candidate post URLs + snippets for this run. Note in the run log that Biostars used the search fallback.
- **SEQanswers** (Cloudflare) — Use the fetcher on the forum index and recent threads: `$NDE_FETCH "https://seqanswers.com/" --html`, then fetch promising thread URLs the same way (with `sleep 7` between). On exit code 2, fall back to `WebSearch site:seqanswers.com`.
- **Reddit r/bioinformatics** — Fetch `https://www.reddit.com/r/bioinformatics/search.json?q=dataset+infectious+disease&sort=new&t=week&limit=25` (try plain `WebFetch` first; if blocked, use the fetcher). Also try queries: "find dataset", "where can I download", "NIH data".
- **Bioconductor Support** — `WebSearch site:support.bioconductor.org dataset infectious disease` for recent threads; fetch promising ones with `WebFetch` (not Cloudflare-protected).

Skip any post whose URL already appears in `memory/seen_posts.json`.

---

## Step 3 — Check tracked threads

For each thread in `memory/thread_registry.json` with status `active`:
1. Fetch the current thread page (use the Cloudflare-aware fetcher for Biostars/SEQanswers URLs, `WebFetch` otherwise)
2. Compare reply count or last activity to `last_checked`
3. If new replies exist, summarize what was added

---

## Step 4 — Score relevance

For each new post, assign a relevance score 1–10:

| Score | Meaning |
|-------|---------|
| 8–10 | Directly asking how to find infectious disease / immune datasets across repositories — NDE is a direct answer |
| 6–7 | Dataset discovery in biomedical context, NIAID/NIH data, multi-repo search — NDE is relevant |
| 4–5 | Tangentially related (general dataset search, not disease-specific) — probably skip |
| 1–3 | Off-topic — skip |

**Only proceed with posts scoring 6 or higher.**

---

## Step 5 — Draft replies for candidates

For each candidate post (score ≥ 6), write a reply that:
- Opens by directly addressing their specific question
- Explains how NDE (data.niaid.nih.gov) can help — be specific, not generic
- Mentions 1–2 concrete capabilities relevant to their question (e.g., unified search, specific repositories indexed, disease ontology support)
- Links to `https://data.niaid.nih.gov` and any relevant search URL if constructable
- Closes with an invitation to ask follow-up questions
- Tone: knowledgeable researcher helping a colleague, not a product pitch
- Length: 2–4 paragraphs

---

## Step 6 — Create GitHub Issues for candidates

For each candidate, run:

```bash
gh issue create \
  --repo NIAID-Data-Ecosystem/NDE-community-crawler \
  --title "[ForumName] <post title>" \
  --label "candidate-reply" \
  --body "..."
```

Issue body format:
```
## Original Post
**Forum:** <name>
**URL:** <url>
**Posted:** <date>
**Relevance score:** <N>/10

### Excerpt
<first 300 chars of post>

---

## Draft Reply

<details>
<summary>Click to expand draft reply</summary>

<draft reply text>

</details>

---

**Action:** Review and edit the draft reply above, post it manually on the forum, then close this issue.
```

Save the returned issue URL.

---

## Step 7 — Discover new forums

Search for communities not already in `config/forums.json` where researchers discuss finding datasets for infectious or immune diseases:
- Try searches like: `forum "infectious disease" "find dataset" site:reddit.com OR site:biostars.org OR site:stackoverflow.com`
- Look for Stack Overflow tags, Discord servers, mailing lists, Slack workspaces

For each promising new community found:
1. Append to `config/forums.json` under `pending`:
```json
{
  "name": "...",
  "url": "...",
  "api": null,
  "notes": "<why this looks relevant>",
  "added_by": "agent",
  "date": "YYYY-MM-DD",
  "rationale": "<evidence: example post or discussion found>"
}
```
2. Create a GitHub Issue:
```bash
gh issue create \
  --repo NIAID-Data-Ecosystem/NDE-community-crawler \
  --title "[Forum Discovery] <community name>" \
  --label "forum-discovery" \
  --body "Agent found a new community that may be worth monitoring. Review config/forums.json and move to 'approved' or 'blocked'.\n\n**URL:** ...\n**Rationale:** ..."
```

---

## Step 8 — Update memory

**`memory/seen_posts.json`** — append all posts examined (candidates and skipped):
```json
{
  "url": "...",
  "title": "...",
  "forum": "...",
  "date_seen": "YYYY-MM-DD",
  "relevance_score": 7,
  "status": "issue_created | skipped",
  "issue_url": "https://github.com/... or null"
}
```

**`memory/thread_registry.json`** — for each candidate post, add an entry to track for followups; update `last_checked` and `reply_count` for existing entries:
```json
{
  "url": "...",
  "title": "...",
  "forum": "...",
  "date_added": "YYYY-MM-DD",
  "last_checked": "YYYY-MM-DD",
  "reply_count": 0,
  "status": "active"
}
```

**`memory/run_log.json`** — append a run summary:
```json
{
  "date": "YYYY-MM-DD",
  "forums_crawled": ["Biostars", "SEQanswers", "..."],
  "posts_examined": 0,
  "candidates": 0,
  "issues_created": 0,
  "threads_checked": 0,
  "new_forums_discovered": 0,
  "errors": [],
  "notes": "..."
}
```

---

## Step 9 — Commit and push

```bash
git -C /home/asu/Science/NDE-community-crawler add memory/ config/
git -C /home/asu/Science/NDE-community-crawler commit -m "Weekly run $(date +%Y-%m-%d): <N> candidates, <M> posts examined"
git -C /home/asu/Science/NDE-community-crawler push
```

---

## Error handling

- **Forum blocked (403/429/CAPTCHA):** For Cloudflare forums this shows up as fetcher **exit code 2** — use the WebSearch fallback for that forum, log it in `run_log.errors`, and continue. If even the fallback fails, skip that forum.
- **GitHub Issue creation fails:** Log error, continue — do not abort the run.
- **Memory file unreadable or malformed:** Treat as empty, log a warning, continue.
- **No candidates found:** That's fine — commit the run log and finish.
