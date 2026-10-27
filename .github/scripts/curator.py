#!/usr/bin/env python3
"""
Autonomous Curator & Trending Engine for Awesome AI.

Enforces the 4 Core Invariants:
1. Safe & Auditable: Strict OSI license whitelist, anti-crack/piracy/NSFW filter.
2. Alive & Active: HTTP 200 liveness probe, not archived/disabled, pushed within 180 days.
3. High Stars: Verified community proof (>= 1,500 stars).
4. Trending Spotlight: Categorization for high-velocity AI agent & productivity repositories.
"""

from datetime import datetime, timezone
import json
import os
import sys
import urllib.parse
import urllib.request

MIN_STARS = 1500
MAX_PUSH_AGE_DAYS = 180

BLACKLIST_KEYWORDS = [
    "activation", "crack", "patch", "keygen", "reset-trial",
    "trial-reset", "license-key", "kms", "bypass", "pirate", "tracker",
    "fuckingfast", "nsfw", "porn", "xxx", "adult", "hentai", "18+",
    "uncensored-nsfw", "deepfake"
]

ALLOWED_LICENSES = {
    "gpl-3.0", "gpl-2.0", "agpl-3.0", "lgpl-3.0",
    "apache-2.0", "mit", "mpl-2.0", "bsd-3-clause", "bsd-2-clause"
}


def get_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Awesome-AI-Curator-Bot"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_json(url):
    req = urllib.request.Request(url, headers=get_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def check_url_alive(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AwesomeCurator/1.0)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 301, 302)
    except Exception:
        return False


def is_blacklisted(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in BLACKLIST_KEYWORDS)


def is_alive_and_active(repo):
    if repo.get("archived") or repo.get("disabled"):
        return False
    pushed_at_str = repo.get("pushed_at")
    if not pushed_at_str:
        return False
    try:
        pushed_date = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - pushed_date).days
        return age_days <= MAX_PUSH_AGE_DAYS
    except Exception:
        return True


def get_existing_readme_content(readme_path="README.md"):
    if not os.path.exists(readme_path):
        return ""
    with open(readme_path, "r", encoding="utf-8") as f:
        return f.read().lower()


def scan_repositories():
    existing_content = get_existing_readme_content()
    queries = [
        f"topic:mcp-server stars:>={MIN_STARS}",
        f"topic:ai-agents stars:>={MIN_STARS}"
    ]

    all_candidates = []
    seen = set()

    for q in queries:
        encoded_q = urllib.parse.quote(q)
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page=15"
        data = fetch_json(url)
        if not data or "items" not in data:
            continue

        for item in data["items"]:
            repo_full = item["full_name"]
            repo_name = item["name"]
            repo_url = item["html_url"].lower()

            if repo_full in seen:
                continue
            seen.add(repo_full)

            if repo_url in existing_content or repo_name.lower() in existing_content:
                continue

            desc = (item.get("description") or "").strip()
            if is_blacklisted(repo_name) or is_blacklisted(desc):
                continue

            license_info = item.get("license") or {}
            license_key = (license_info.get("key") or "").lower()
            if license_key not in ALLOWED_LICENSES:
                continue

            if not is_alive_and_active(item):
                continue

            if not check_url_alive(item["html_url"]):
                continue

            stars = item["stargazers_count"]
            trending_tag = "🚀 Monthly Powerhouse" if stars >= 15000 else (
                "⚡ Weekly High-Velocity" if stars >= 5000 else "🌟 Active Innovator"
            )

            all_candidates.append({
                "name": item["name"],
                "url": item["html_url"],
                "description": desc,
                "stars": stars,
                "license": license_info.get("spdx_id") or license_key.upper(),
                "language": item.get("language") or "N/A",
                "trending_category": trending_tag
            })

    return all_candidates


def generate_report(candidates, output_file="curator_summary.md"):
    if not candidates:
        print("All candidate repositories are already up to date. Exiting cleanly.")
        return False

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("### 🤖 Autonomous Curator — Verified AI & Agent Findings\n\n")
        f.write(f"Verified **{len(candidates)}** candidate(s) satisfying all 4 Invariants:\n\n")
        f.write("| Category | Project | Stars | License | Language | Description |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for c in candidates:
            f.write(f"| {c['trending_category']} | [**{c['name']}**]({c['url']}) | ⭐ {c['stars']:,} | `{c['license']}` | {c['language']} | {c['description']} |\n")

    return True


if __name__ == "__main__":
    candidates = scan_repositories()
    has_items = generate_report(candidates)
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"found={'true' if has_items else 'false'}\n")
            f.write(f"count={len(candidates)}\n")
