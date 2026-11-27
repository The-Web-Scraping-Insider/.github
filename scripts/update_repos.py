"""Rebuild the projects table in profile/README.md from the org's public repos.

Replaces everything between <!-- REPOS:START ... --> and <!-- REPOS:END -->.
Uses each repo's GitHub description as the "What it is" text.
"""
import json
import os
import re
import sys
import urllib.request

ORG = os.environ.get("ORG", "The-Web-Scraping-Insider")
README = os.environ.get("README_PATH", "profile/README.md")
SKIP = {".github"}
# Used only when a repo has no description set on GitHub
FALLBACK_DESCRIPTIONS = {
    "web-scraping-expert-amas": "Cleaned transcripts and a structured Q&A dataset from the expert AMAs on r/WebScrapingInsider: proxy providers, anti-bot engineers, AI-agent builders and more.",
}


def fetch_repos():
    repos, page = [], 1
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-bot"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?type=public&per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
            batch = json.load(r)
        if not batch:
            return repos
        repos += batch
        page += 1


def build_table(repos):
    keep = [r for r in repos
            if not r["private"] and not r["fork"] and not r["archived"] and r["name"] not in SKIP]
    # Most-starred first, then oldest first
    keep.sort(key=lambda r: (-r["stargazers_count"], r["created_at"]))
    rows = ["| Repo | What it is |", "| --- | --- |"]
    for r in keep:
        desc = (r["description"] or FALLBACK_DESCRIPTIONS.get(r["name"], "")).replace("|", "\\|").strip() or "Coming soon."
        rows.append(f"| [{r['name']}]({r['html_url']}) | {desc} |")
    return "\n".join(rows)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(r"(<!-- REPOS:START.*?-->\n).*?(\n<!-- REPOS:END -->)", re.S)
    if not pattern.search(text):
        sys.exit("REPOS:START / REPOS:END markers not found in README")
    new = pattern.sub(lambda m: m.group(1) + build_table(fetch_repos()) + m.group(2), text)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
