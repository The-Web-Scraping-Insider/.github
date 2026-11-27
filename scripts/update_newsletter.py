"""Rebuild the latest-issues list in profile/README.md from the Beehiiv newsletter.

Replaces everything between <!-- NEWSLETTER:START ... --> and <!-- NEWSLETTER:END -->.

Issue URLs come from the publication's public sitemap (every post lives under /p/);
each issue page is then read for its og:title, og:description and article:published_time.
No Beehiiv API key needed.

If nothing can be fetched (Beehiiv down, blocked, etc.) the README is left untouched,
so a bad run never wipes the list.
"""
import html
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

SITE = os.environ.get("BEEHIIV_URL", "https://thewebscrapinginsider.beehiiv.com").rstrip("/")
README = os.environ.get("README_PATH", "profile/README.md")
LIMIT = int(os.environ.get("NEWSLETTER_LIMIT", "5"))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebScrapingInsiderProfileBot/1.0; "
                  "+https://github.com/The-Web-Scraping-Insider)",
    "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8",
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def meta(page, prop):
    # Handles either attribute order: property/name before or after content
    for pat in (rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]*)"',
                rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{prop}"'):
        m = re.search(pat, page, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return None


def issue_urls():
    sitemap = get(f"{SITE}/sitemap.xml")
    urls = re.findall(r"<loc>\s*([^<\s]+/p/[^<\s]+)\s*</loc>", sitemap)
    return list(dict.fromkeys(urls))  # de-dupe, keep order


def read_issue(url):
    try:
        page = get(url)
    except Exception as e:  # one bad page shouldn't sink the run
        print(f"  skip {url}: {e}", file=sys.stderr)
        return None
    title = meta(page, "og:title")
    published = meta(page, "article:published_time")
    if not title or not published:
        print(f"  skip {url}: missing title/date", file=sys.stderr)
        return None
    try:
        date = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        print(f"  skip {url}: bad date {published!r}", file=sys.stderr)
        return None
    description = meta(page, "og:description") or meta(page, "description") or ""
    return {"url": url, "title": title, "date": date, "description": description}


def fetch_issues():
    urls = issue_urls()
    with ThreadPoolExecutor(max_workers=4) as pool:
        issues = [i for i in pool.map(read_issue, urls) if i]
    issues.sort(key=lambda i: i["date"], reverse=True)
    return issues[:LIMIT]


def build_list(issues):
    lines = []
    for i in issues:
        title = i["title"].replace("[", "\\[").replace("]", "\\]")
        lines.append(f"- **[{title}]({i['url']})** · {i['date']:%b %-d, %Y}")
        desc = " ".join(i["description"].split())
        if desc:
            lines[-1] += "  "  # markdown line break inside the list item
            lines.append(f"  {desc}")
    lines.append("")
    lines.append(f"[Browse all issues →]({SITE}/archive)")
    return "\n".join(lines)


def main():
    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(r"(<!-- NEWSLETTER:START.*?-->\n)(?:.*?\n)?(<!-- NEWSLETTER:END -->)", re.S)
    if not pattern.search(text):
        sys.exit("NEWSLETTER:START / NEWSLETTER:END markers not found in README")

    try:
        issues = fetch_issues()
    except Exception as e:
        print(f"Could not reach Beehiiv ({e}); leaving README unchanged")
        return
    if not issues:
        print("No issues found; leaving README unchanged")
        return

    new = pattern.sub(lambda m: m.group(1) + build_list(issues) + "\n" + m.group(2), text)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"README updated with {len(issues)} issues")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
