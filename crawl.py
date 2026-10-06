#!/usr/bin/env python3
"""
NDE Community Crawler — standalone manual run script.
Usage: python crawl.py

Crawls approved forums for posts about infectious disease dataset discovery,
scores relevance, and creates GitHub Issues for candidates via gh CLI.
No Claude API key required.
"""

import gzip
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

REPO = Path(__file__).parent
MEMORY = REPO / "memory"
CONFIG = REPO / "config" / "forums.json"

GH_REPO = "NIAID-Data-Ecosystem/NDE-community-crawler"
GH_CLI = r"C:\Program Files\GitHub CLI\gh.exe"

RELEVANCE_THRESHOLD = 6

# Strong signals: post is explicitly seeking a resource
KEYWORDS_SEEKING = [
    "where can i find", "looking for", "where to find", "how do i find",
    "where do i get", "is there a database", "is there a tool", "is there a resource",
    "does anyone know of", "any recommendations for", "any suggestions for",
    "recommend a", "looking for a tool", "looking for software", "looking for data",
    "looking for samples", "find dataset", "find data", "find samples",
    "access data", "download data", "get data", "obtain data",
    "public dataset", "open dataset", "available dataset", "publicly available",
    "data repository", "database for", "resource for",
]

# Resource types — only score if combined with a seeking signal or disease term
KEYWORDS_RESOURCE = [
    # data
    "dataset", "data repository", "genomics data", "sequencing data",
    "clinical data", "biomedical data", "omics data", "ngs data",
    "rna-seq data", "wgs data", "proteomics data", "multi-omics",
    # samples / biospecimens
    "biospecimen", "biobank", "specimen", "biological sample",
    "patient sample", "clinical sample", "isolate", "strain collection",
    "culture collection", "patient isolate", "clinical isolate",
    # tools / software
    "bioinformatics tool", "bioinformatics software", "analysis tool",
    "computational tool", "open source tool", "web tool", "web server",
    "command line tool", "software package", "r package", "python package",
    # other resources
    "protein structure", "genome sequence", "reference genome",
    "annotation database", "ontology", "knowledgebase",
]

# Disease / NIAID relevance
KEYWORDS_DISEASE = [
    "infectious disease", "infectious", "pathogen", "virus", "viral",
    "bacteria", "bacterial", "fungal", "parasite", "parasitic",
    "immune", "immunology", "immunological", "niaid", "nih",
    "covid", "sars", "sars-cov", "hiv", "influenza", "flu",
    "malaria", "tuberculosis", "tb", "ebola", "zika", "dengue",
    "hepatitis", "hcv", "hbv", "mpox", "monkeypox",
    "antimicrobial", "antibiotic resistance", "amr",
]

# Explicit NDE/NIAID mentions — always high value
KEYWORDS_NDE = [
    "niaid", "nde", "data.niaid.nih.gov", "immport",
    "niaid data", "niaid funded", "nih data ecosystem",
]

# Methodology/career posts — penalize these (not resource-seeking)
KEYWORDS_PENALTY = [
    "how do i analyze", "how to analyze", "how do i run", "how to run",
    "statistical power", "sample size", "normalization", "batch correction",
    "differential expression", "clustering", "dimensionality reduction",
    "machine learning model", "deep learning model", "training a model",
    "qc criteria", "quality control", "preprocessing", "alignment",
    "how to learn", "roadmap for", "career advice", "getting started with",
    "solo bioinformatician", "improve my skills", "benchmarked",
    "how do i interpret", "how to interpret", "what does this mean",
    "is this normal", "expected result", "troubleshoot",
]

SEARCH_QUERIES = [
    "looking for infectious disease dataset",
    "where can I find pathogen data",
    "find dataset NIH NIAID",
    "where to get virus sequencing data",
    "looking for immunology dataset",
    "find samples infectious disease",
    "biobank pathogen samples",
    "looking for bioinformatics tool infectious disease",
    "where to find genome sequence pathogen",
    "open dataset virus clinical",
]

UA = "NDE-crawler/1.0 (research bot; +https://data.niaid.nih.gov)"


# ── helpers ───────────────────────────────────────────────────────────────────

def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            if r.info().get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARN fetch {url}: {e}", file=sys.stderr)
        return ""


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def seven_days_ago_epoch():
    return int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())


# ── relevance scoring ─────────────────────────────────────────────────────────

def score_post(title, body):
    title_lower = title.lower()
    text = (title_lower + " " + body.lower())
    score = 0

    # NDE/NIAID mentions — always strongly relevant
    nde_hits = sum(1 for kw in KEYWORDS_NDE if kw in text)
    score += nde_hits * 4

    # Resource-seeking signals (the core intent we want)
    seeking_hits = sum(1 for kw in KEYWORDS_SEEKING if kw in text)
    score += min(seeking_hits * 2, 6)

    # Resource type mentions (only meaningful alongside seeking/disease context)
    resource_hits = sum(1 for kw in KEYWORDS_RESOURCE if kw in text)
    score += min(resource_hits, 4)

    # Disease relevance
    disease_hits = sum(1 for kw in KEYWORDS_DISEASE if kw in text)
    score += min(disease_hits * 2, 4)

    # Penalty for methodology/career/workflow posts
    penalty_hits = sum(1 for kw in KEYWORDS_PENALTY if kw in text)
    score -= penalty_hits * 3

    # A post with resource types but NO seeking signal and NO disease term
    # is likely a methods post — apply extra penalty
    if seeking_hits == 0 and disease_hits == 0 and nde_hits == 0:
        score -= 4

    score = max(0, min(score, 10))
    return score


# ── forum crawlers ────────────────────────────────────────────────────────────

def crawl_stack_exchange(site, tagged=None):
    posts = []
    fromdate = seven_days_ago_epoch()
    for query in SEARCH_QUERIES:
        params = {
            "order": "desc", "sort": "creation",
            "q": query, "site": site,
            "pagesize": "25", "filter": "withbody",
            "fromdate": str(fromdate),
        }
        if tagged:
            params["tagged"] = tagged
        url = "https://api.stackexchange.com/2.3/search/advanced?" + urllib.parse.urlencode(params)
        raw = fetch(url)
        if not raw:
            continue
        try:
            data = json.loads(raw)
            for item in data.get("items", []):
                posts.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "body": re.sub(r"<[^>]+>", " ", item.get("body", ""))[:800],
                    "date": datetime.fromtimestamp(item.get("creation_date", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "forum": site,
                })
        except Exception as e:
            print(f"  WARN parse SE {site}: {e}", file=sys.stderr)
    return posts


def crawl_galaxy():
    posts = []
    for query in ["infectious disease dataset", "find dataset", "NIAID"]:
        url = f"https://help.galaxyproject.org/search.json?q={urllib.parse.quote_plus(query)}"
        raw = fetch(url, {"Accept": "application/json"})
        if not raw:
            continue
        try:
            data = json.loads(raw)
            for p in data.get("posts", []):
                topic_id = p.get("topic_id")
                posts.append({
                    "title": p.get("topic_title_headline", p.get("blurb", ""))[:120],
                    "url": f"https://help.galaxyproject.org/t/{topic_id}",
                    "body": p.get("blurb", ""),
                    "date": p.get("created_at", "")[:10],
                    "forum": "Galaxy Help Forum",
                })
        except Exception as e:
            print(f"  WARN parse Galaxy: {e}", file=sys.stderr)
    return posts


def _crawl_reddit_sub(subreddit, queries, headers):
    posts = []
    for query in queries:
        url = (
            f"https://www.reddit.com/r/{subreddit}/search.json"
            f"?q={urllib.parse.quote_plus(query)}&sort=new&t=week&limit=25&restrict_sr=1"
        )
        raw = fetch(url, headers)
        if not raw or ('"kind": "Listing"' not in raw and "reddit.com/login" in raw):
            print(f"  Reddit r/{subreddit}: blocked — check REDDIT_SESSION in .env", file=sys.stderr)
            break
        try:
            data = json.loads(raw)
            for child in data.get("data", {}).get("children", []):
                p = child.get("data", {})
                posts.append({
                    "title": p.get("title", ""),
                    "url": "https://www.reddit.com" + p.get("permalink", ""),
                    "body": p.get("selftext", "")[:800],
                    "date": datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                    "forum": f"Reddit r/{subreddit}",
                })
        except Exception as e:
            print(f"  WARN parse Reddit r/{subreddit}: {e}", file=sys.stderr)
    return posts


def crawl_reddit():
    session_cookie = os.getenv("REDDIT_SESSION", "").strip()
    headers = {"Accept": "application/json"}
    if session_cookie:
        headers["Cookie"] = f"reddit_session={session_cookie}"
    else:
        print("  Reddit: no REDDIT_SESSION in .env — requests may be blocked", file=sys.stderr)

    posts = []
    posts += _crawl_reddit_sub("bioinformatics", SEARCH_QUERIES[:3], headers)
    posts += _crawl_reddit_sub("datasets", [
        "infectious disease", "genomics", "pathogen", "NIH", "biomedical",
        "virus", "immunology", "clinical data",
    ], headers)
    return posts


# ── deduplication ─────────────────────────────────────────────────────────────

def dedup(posts, seen_urls):
    seen = set(seen_urls)
    out = []
    for p in posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            out.append(p)
    return out


# ── draft reply ───────────────────────────────────────────────────────────────

def draft_reply(post):
    return (
        f"The NIAID Data Ecosystem (NDE) at https://data.niaid.nih.gov may be useful here — "
        f"it provides unified search across dozens of NIAID-funded repositories including ImmPort, "
        f"NCBI, ClinicalTrials.gov, ViPR, and more, covering datasets, biological samples, and "
        f"computational tools for infectious and immune-related diseases.\n\n"
        f"A search for terms related to your question ({post['title'][:60]}...) will surface "
        f"resources from repositories you might not find through a standard PubMed or GEO search. "
        f"The platform supports filtering by disease, data type, and organism, and links directly "
        f"to the source repository.\n\n"
        f"Happy to help narrow down further if you can share more about the specific pathogen, "
        f"data type, or analysis you're working on!"
    )


# ── GitHub Issue creation ─────────────────────────────────────────────────────

def create_issue(post, reply):
    title = f"[{post['forum']}] {post['title'][:80]}"
    body = f"""## Original Post
**Forum:** {post['forum']}
**URL:** {post['url']}
**Posted:** {post['date']}
**Relevance score:** {post['score']}/10

### Excerpt
{post['body'][:300]}

---

## Draft Reply

<details>
<summary>Click to expand draft reply</summary>

{reply}

</details>

---

**Action:** Review and edit the draft reply above, post it manually on the forum, then close this issue.
"""
    gh = GH_CLI if os.path.exists(GH_CLI) else "gh"
    try:
        result = subprocess.run(
            [gh, "issue", "create",
             "--repo", GH_REPO,
             "--title", title,
             "--label", "candidate-reply",
             "--body", body],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  gh error: {result.stderr.strip()}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  gh failed: {e}", file=sys.stderr)
        return None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== NDE Community Crawler — {today} ===\n")

    seen_posts = load_json(MEMORY / "seen_posts.json", [])
    run_log = load_json(MEMORY / "run_log.json", [])
    seen_urls = {p["url"] for p in seen_posts}

    # Crawl
    all_posts = []
    print("Crawling Bioinformatics Stack Exchange...")
    all_posts += crawl_stack_exchange("bioinformatics")
    print(f"  {len(all_posts)} posts so far")

    print("Crawling Stack Overflow (bioinformatics tag)...")
    so_posts = crawl_stack_exchange("stackoverflow", tagged="bioinformatics")
    all_posts += so_posts
    print(f"  +{len(so_posts)} posts")

    print("Crawling Galaxy Help Forum...")
    gal_posts = crawl_galaxy()
    all_posts += gal_posts
    print(f"  +{len(gal_posts)} posts")

    print("Crawling Reddit r/bioinformatics...")
    reddit_posts = crawl_reddit()
    all_posts += reddit_posts
    print(f"  +{len(reddit_posts)} posts")

    # Dedup
    new_posts = dedup(all_posts, seen_urls)
    print(f"\n{len(new_posts)} new posts to evaluate (after dedup)\n")

    # Score
    candidates = []
    skipped = []
    for p in new_posts:
        p["score"] = score_post(p["title"], p["body"])
        if p["score"] >= RELEVANCE_THRESHOLD:
            candidates.append(p)
        else:
            skipped.append(p)

    print(f"Candidates (score >= {RELEVANCE_THRESHOLD}): {len(candidates)}")
    for c in candidates:
        print(f"  [{c['score']}/10] {c['title'][:80]}")
    print(f"Skipped: {len(skipped)}\n")

    # Create issues
    issues_created = 0
    new_seen = []

    for post in candidates:
        reply = draft_reply(post)
        print(f"Creating issue for: {post['title'][:60]}...")
        issue_url = create_issue(post, reply)
        if issue_url:
            print(f"  Created: {issue_url}")
            issues_created += 1
        new_seen.append({
            "url": post["url"],
            "title": post["title"],
            "forum": post["forum"],
            "date_seen": today,
            "relevance_score": post["score"],
            "status": "issue_created" if issue_url else "candidate_no_issue",
            "issue_url": issue_url,
            "notes": "",
        })

    for post in skipped:
        new_seen.append({
            "url": post["url"],
            "title": post["title"],
            "forum": post["forum"],
            "date_seen": today,
            "relevance_score": post["score"],
            "status": "skipped",
            "issue_url": None,
            "notes": "",
        })

    # Update memory
    seen_posts.extend(new_seen)
    save_json(MEMORY / "seen_posts.json", seen_posts)

    errors = []
    run_log.append({
        "date": today,
        "run": len(run_log) + 1,
        "forums_crawled": ["Bioinformatics Stack Exchange", "Stack Overflow (bioinformatics tag)", "Galaxy Help Forum", "Reddit r/bioinformatics", "Reddit r/datasets"],
        "posts_examined": len(new_posts),
        "candidates": len(candidates),
        "issues_created": issues_created,
        "threads_checked": 0,
        "new_forums_discovered": 0,
        "errors": errors,
        "notes": f"Manual run via crawl.py. {len(new_posts)} new posts, {len(candidates)} candidates, {issues_created} issues created.",
    })
    save_json(MEMORY / "run_log.json", run_log)

    # Commit
    print("\nCommitting memory updates...")
    try:
        subprocess.run(["git", "-C", str(REPO), "add", "memory/"], check=True)
        msg = f"Weekly crawl {today}: {len(candidates)} candidates, {len(new_posts)} posts examined"
        result = subprocess.run(["git", "-C", str(REPO), "commit", "-m", msg],
                                capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(["git", "-C", str(REPO), "push"], check=True)
            print("  Pushed.")
        else:
            print("  Nothing to commit.")
    except Exception as e:
        print(f"  Git error: {e}", file=sys.stderr)

    print(f"\nDone. {len(new_posts)} examined, {len(candidates)} candidates, {issues_created} issues created.")


if __name__ == "__main__":
    main()
