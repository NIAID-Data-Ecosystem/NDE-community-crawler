#!/usr/bin/env python3
"""Search Bioconductor Support forum.

Bioconductor Support uses a modified Biostar platform (not Discourse).
This scraper tries multiple endpoint patterns and falls back to WebSearch.
"""
import sys
import json
import subprocess
import urllib.parse

SEARCH_TERMS = [
    "infectious disease dataset",
    "NIAID",
    "find dataset pathogen",
    "immunology dataset",
    "virus sequencing data",
]
BASE_URL = "https://support.bioconductor.org"
HEADERS = [
    "-A", "Mozilla/5.0 (compatible; NDE-crawler/1.0; +https://data.niaid.nih.gov)",
    "-H", "Accept: application/json",
    "-H", "X-Requested-With: XMLHttpRequest",
]


def _curl(url, extra_flags=None):
    cmd = ["curl", "-s", "--max-time", "15"] + HEADERS
    if extra_flags:
        cmd += extra_flags
    cmd.append(url)
    try:
        out = subprocess.check_output(cmd, timeout=20, stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return b""


def search_bioconductor():
    results = []
    seen_ids = set()

    for term in SEARCH_TERMS:
        encoded = urllib.parse.quote_plus(term)

        # Try Biostar-style search API
        raw = _curl(f"{BASE_URL}/search/similar/?query={encoded}&limit=20")
        if raw:
            try:
                data = json.loads(raw)
                posts = data if isinstance(data, list) else data.get("results", [])
                for p in posts:
                    pid = p.get("id") or p.get("uid")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    results.append({
                        "title": p.get("title", ""),
                        "url": f"{BASE_URL}/p/{pid}/",
                        "date": p.get("creation_date", "")[:10],
                        "body": p.get("content", "")[:600],
                        "forum": "Bioconductor Support",
                    })
                continue
            except json.JSONDecodeError:
                pass

        # Try tag-based API (Biostar REST)
        raw = _curl(f"{BASE_URL}/api/post/?type=question&limit=25&days=7&tag={encoded}")
        if raw:
            try:
                data = json.loads(raw)
                for p in data.get("results", []):
                    pid = p.get("id")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    results.append({
                        "title": p.get("title", ""),
                        "url": f"{BASE_URL}/p/{pid}/",
                        "date": p.get("creation_date", "")[:10],
                        "body": p.get("content", "")[:600],
                        "forum": "Bioconductor Support",
                    })
            except json.JSONDecodeError:
                pass

    if not results:
        print(
            "Bioconductor: no results via API. Forum may require session auth. "
            "Consider adding BIOCONDUCTOR_SESSION_COOKIE to .env.",
            file=sys.stderr,
        )

    return results


if __name__ == "__main__":
    posts = search_bioconductor()
    print(json.dumps(posts, indent=2))
