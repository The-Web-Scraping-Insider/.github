"""Rebuild the recent AMAs list in profile/README.md.

Replaces everything between <!-- AMAS:START ... --> and <!-- AMAS:END -->
using the public metadata in web-scraping-expert-amas/data/amas.json.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date

ORG = os.environ.get("ORG", "The-Web-Scraping-Insider")
AMA_REPO = os.environ.get("AMA_REPO", "web-scraping-expert-amas")
README = os.environ.get("README_PATH", "profile/README.md")
LIMIT = int(os.environ.get("AMA_LIMIT", "6"))
REPO_URL = f"https://github.com/{ORG}/{AMA_REPO}"
DATA_URL = f"https://raw.githubusercontent.com/{ORG}/{AMA_REPO}/main/data/amas.json"


def fetch_amas():
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def guest_line(guests):
    """Short guest label, e.g. "Jason Grad (Massive)" or "Batuhan Özyön + team (Scrape.do)"."""
    names = [g["name"] for g in guests if g.get("name") and "team" not in g["name"].lower()]
    companies = []
    for g in guests:
        c = (g.get("company") or "").strip()
        if c and c.lower() not in {"freelance", "independent"} and c not in companies:
            companies.append(c)
    who = names[0] + " + team" if len(guests) > 2 and names else " & ".join(names)
    if companies:
        return f"{who} ({', '.join(companies)})" if who else f"{companies[0]} team"
    return who


def build_list(amas):
    total = len(amas)
    amas = sorted(amas, key=lambda a: (a["date"], a["number"]), reverse=True)[:LIMIT]
    lines = []
    for a in amas:
        when = date.fromisoformat(a["date"]).strftime("%b %-d, %Y")
        links = [f"[Reddit thread]({a['reddit']})",
                 f"[Transcript]({REPO_URL}/blob/main/{a['transcript']})"]
        if a.get("article"):
            links.append(f"[Insights article]({a['article']})")
        guests = guest_line(a.get("guests", []))
        meta = " · ".join(x for x in [guests, when, f"{a['questions_answered']} Q&As"] if x)
        lines.append(f"- **{a['title']}** · {meta}  \n  " + " · ".join(links))
    lines.append("")
    lines.append(f"[All {total} AMAs, transcripts and Q&A dataset →]({REPO_URL})")
    return "\n".join(lines)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(r"(<!-- AMAS:START.*?-->\n).*?(\n?<!-- AMAS:END -->)", re.S)
    if not pattern.search(text):
        sys.exit("AMAS:START / AMAS:END markers not found in README")
    amas = fetch_amas()
    new = pattern.sub(lambda m: m.group(1) + build_list(amas) + m.group(2), text)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
