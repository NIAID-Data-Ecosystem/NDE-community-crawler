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

**Per-forum crawl strategy:**

Use `curl` via Bash for all forum requests — do NOT use WebFetch. WebFetch does not support custom headers and will be blocked with HTTP 403. Always set a descriptive User-Agent.

- **Biostars** — Use curl to query the REST API with multiple search terms. The API requires a browser-like User-Agent:
  ```bash
  curl -s --max-time 15 \
    -A "Mozilla/5.0 (compatible; NDE-crawler/1.0; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://www.biostars.org/api/post/?type=question&limit=50&days=7&tag=dataset"
  curl -s --max-time 15 \
    -A "Mozilla/5.0 (compatible; NDE-crawler/1.0; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://www.biostars.org/api/post/?type=question&limit=50&days=7&tag=infectious+disease"
  ```
  Parse JSON: each result has `id`, `title`, `url`, `tag_val`, `creation_date`. Construct post URL as `https://www.biostars.org/p/<id>/`.

- **SEQanswers** — Fetch the recent threads page with a full browser User-Agent:
  ```bash
  curl -s --max-time 15 \
    -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
    -H "Accept-Language: en-US,en;q=0.5" \
    -L "https://seqanswers.com/forum/bioinformatics/bioinformatics-aa"
  ```
  Parse HTML for thread titles and links. If still blocked (403/429), log it and skip.

- **Reddit r/bioinformatics** — Reddit requires a descriptive User-Agent per their API rules. Use OAuth-free JSON endpoints:
  ```bash
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot monitoring dataset discovery questions; contact nde@niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://www.reddit.com/r/bioinformatics/search.json?q=dataset+infectious+disease&sort=new&t=week&limit=25&restrict_sr=1"
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot monitoring dataset discovery questions; contact nde@niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://www.reddit.com/r/bioinformatics/search.json?q=find+dataset+NIH&sort=new&t=week&limit=25&restrict_sr=1"
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot monitoring dataset discovery questions; contact nde@niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://www.reddit.com/r/bioinformatics/search.json?q=where+download+data+disease&sort=new&t=week&limit=25&restrict_sr=1"
  ```
  Parse JSON: `data.children[].data` contains `title`, `url`, `permalink`, `selftext`, `created_utc`.

- **Bioconductor Support** — Use the Discourse JSON API directly:
  ```bash
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://support.bioconductor.org/search.json?q=infectious+disease+dataset"
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://support.bioconductor.org/latest.json?category=&period=weekly"
  ```
  Parse JSON for recent topic titles, urls, and creation dates.

- **Galaxy Help Forum** — Use the Discourse JSON API:
  ```bash
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://help.galaxyproject.org/search.json?q=infectious+disease+dataset"
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    -H "Accept: application/json" \
    "https://help.galaxyproject.org/latest.json?period=weekly"
  ```

- **Bioinformatics Stack Exchange** — Use the Stack Exchange API (no auth required for read):
  ```bash
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    "https://api.stackexchange.com/2.3/questions?order=desc&sort=creation&tagged=dataset&site=bioinformatics&pagesize=50&filter=withbody&fromdate=$(date -d '7 days ago' +%s 2>/dev/null || date -v-7d +%s)"
  ```
  Parse JSON: `items[].title`, `items[].link`, `items[].body`, `items[].creation_date`.

- **Stack Overflow (bioinformatics tag)** — Use the Stack Exchange API:
  ```bash
  curl -s --max-time 15 \
    -A "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)" \
    "https://api.stackexchange.com/2.3/questions?order=desc&sort=creation&tagged=bioinformatics;dataset&site=stackoverflow&pagesize=25&filter=withbody&fromdate=$(date -d '7 days ago' +%s 2>/dev/null || date -v-7d +%s)"
  ```

Skip any post whose URL already appears in `memory/seen_posts.json`.

---

## Step 3 — Check tracked threads

For each thread in `memory/thread_registry.json` with status `active`:
1. Fetch the current thread page
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

- **Forum blocked (403/429/CAPTCHA):** Log in `run_log.errors`, skip that forum, continue.
- **GitHub Issue creation fails:** Log error, continue — do not abort the run.
- **Memory file unreadable or malformed:** Treat as empty, log a warning, continue.
- **No candidates found:** That's fine — commit the run log and finish.
