# NDE Community Crawler

Agentic weekly crawler that discovers community forum posts relevant to the NIAID Data Ecosystem (data.niaid.nih.gov) and drafts replies for human review.

## What this project does

Each week, an agent crawls approved forums (Biostars, SEQanswers, Reddit r/bioinformatics, etc.) for posts where researchers are looking for infectious disease or immune-related datasets. Relevant posts become GitHub Issues with draft replies for a human to review and post manually.

## Key files

- `config/forums.json` — **human-editable** list of approved/pending/blocked forums
- `memory/seen_posts.json` — all posts ever examined, with relevance scores and status
- `memory/thread_registry.json` — threads being tracked for followup replies
- `memory/run_log.json` — weekly run history
- `prompts/weekly_run.md` — the full agent prompt executed each week

## Running manually

```bash
claude --print < prompts/weekly_run.md
```

## Managing forums

To add a forum manually, edit `config/forums.json` and add to `approved`:
```json
{
  "name": "Forum Name",
  "url": "https://...",
  "api": null,
  "notes": "Why this is relevant",
  "added_by": "human"
}
```

To block an agent-discovered forum, move it from `pending` to `blocked` and add a `reason` field.

## GitHub Issue labels

- `candidate-reply` — a post the agent found and drafted a reply for
- `forum-discovery` — a new community the agent suggests monitoring

## Environment

Requires `gh` CLI authenticated to the NIAID-Data-Ecosystem org.
