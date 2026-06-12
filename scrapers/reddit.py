#!/usr/bin/env python3
"""Search Reddit r/bioinformatics using PRAW with OAuth (read-only script app)."""
import sys
import os
import json
import datetime

try:
    import praw
    from dotenv import load_dotenv
except ImportError as e:
    print(json.dumps({"error": f"Missing dependency: {e}. Run: pip install praw python-dotenv"}))
    sys.exit(1)

load_dotenv()

SEARCH_QUERIES = [
    "infectious disease dataset",
    "find dataset NIH",
    "NIAID data repository",
    "where download sequencing data disease",
    "dataset pathogen immunology",
]
SUBREDDIT = "bioinformatics"


def search_reddit(days=7):
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "ERROR: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET not set. "
            "See docs/setup.md for instructions.",
            file=sys.stderr,
        )
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="NDE-crawler/1.0 (infectious disease dataset monitoring; contact nde@niaid.nih.gov)",
    )

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    results = []
    seen_ids = set()

    sub = reddit.subreddit(SUBREDDIT)
    for query in SEARCH_QUERIES:
        try:
            for post in sub.search(query, sort="new", time_filter="week", limit=25):
                if post.id in seen_ids:
                    continue
                seen_ids.add(post.id)
                post_date = datetime.datetime.utcfromtimestamp(post.created_utc)
                if post_date < cutoff:
                    continue
                results.append(
                    {
                        "title": post.title,
                        "url": f"https://www.reddit.com{post.permalink}",
                        "date": post_date.strftime("%Y-%m-%d"),
                        "body": post.selftext[:600],
                        "forum": "Reddit r/bioinformatics",
                        "score": post.score,
                        "num_comments": post.num_comments,
                    }
                )
        except Exception as e:
            print(f"Error searching '{query}': {e}", file=sys.stderr)

    return results


if __name__ == "__main__":
    posts = search_reddit()
    print(json.dumps(posts, indent=2))
