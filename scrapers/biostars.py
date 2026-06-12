#!/usr/bin/env python3
"""Search Biostars using their REST API with an API key.

Biostars is behind Cloudflare and requires an API key to bypass it.
Get your key from: https://www.biostars.org/accounts/profile/ (under API key section).
Set BIOSTARS_API_KEY in .env.
"""
import sys
import os
import json

try:
    from curl_cffi import requests
    from dotenv import load_dotenv
except ImportError as e:
    print(json.dumps({"error": f"Missing dependency: {e}. Run: pip install curl-cffi python-dotenv"}))
    sys.exit(1)

load_dotenv()

SEARCH_TAGS = ["dataset", "infectious-disease", "niaid", "public-data"]
SEARCH_TERMS = ["infectious disease dataset", "NIAID data", "find sequencing data pathogen"]
BASE_API = "https://www.biostars.org/api/post/"


def search_biostars(days=7):
    api_key = os.getenv("BIOSTARS_API_KEY")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"
    else:
        print(
            "WARNING: BIOSTARS_API_KEY not set — requests will be blocked by Cloudflare. "
            "See docs/setup.md.",
            file=sys.stderr,
        )

    session = requests.Session(impersonate="chrome120")
    results = []
    seen_ids = set()

    for tag in SEARCH_TAGS:
        try:
            resp = session.get(
                BASE_API,
                params={"type": "question", "limit": 50, "days": days, "tag": tag},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("results", []):
                    pid = post.get("id")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    results.append(
                        {
                            "title": post.get("title", ""),
                            "url": f"https://www.biostars.org/p/{pid}/",
                            "date": post.get("creation_date", "")[:10],
                            "body": post.get("content", "")[:600],
                            "forum": "Biostars",
                            "tags": post.get("tag_val", ""),
                        }
                    )
            elif resp.status_code in (403, 429):
                print(
                    f"Biostars blocked (HTTP {resp.status_code}) for tag={tag}. "
                    "Ensure BIOSTARS_API_KEY is set.",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"Error fetching tag={tag}: {e}", file=sys.stderr)

    return results


if __name__ == "__main__":
    posts = search_biostars()
    print(json.dumps(posts, indent=2))
