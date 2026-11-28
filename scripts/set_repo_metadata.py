"""Apply description, homepage and topics from shared/org.yml to every org repo.

Usage (needs the gh CLI, logged in with admin rights on the org's repos):
    python3 scripts/set_repo_metadata.py            # dry run: show what would change
    python3 scripts/set_repo_metadata.py --apply    # make the changes

Topics are replaced with common_topics + the repo's own topics, so put every topic
you want to keep in shared/org.yml.
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "shared" / "org.yml").read_text(encoding="utf-8"))
OWNER = CFG["org"]["url"].rstrip("/").split("/")[-1]


def gh(*args, data=None):
    cmd = ["gh", "api", *args]
    if data is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(data) if data is not None else None,
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gh api {' '.join(args)} failed: {r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def main():
    apply = "--apply" in sys.argv
    for repo in CFG["repos"]:
        name = repo["name"]
        want_desc = " ".join((repo.get("description") or "").split())
        want_home = CFG["homepage"]
        want_topics = list(dict.fromkeys(CFG["common_topics"] + repo.get("topics", [])))[:20]
        cur = gh(f"repos/{OWNER}/{name}")
        changes = {}
        if (cur.get("description") or "") != want_desc:
            changes["description"] = want_desc
        if (cur.get("homepage") or "") != want_home:
            changes["homepage"] = want_home
        topics_change = sorted(cur.get("topics", [])) != sorted(want_topics)

        print(f"\n== {name}")
        if not changes and not topics_change:
            print("   up to date")
            continue
        for k, v in changes.items():
            print(f"   {k}: {cur.get(k)!r}\n      -> {v!r}")
        if topics_change:
            print(f"   topics: {sorted(cur.get('topics', []))}\n      -> {want_topics}")
        if apply:
            if changes:
                gh("-X", "PATCH", f"repos/{OWNER}/{name}", data=changes)
            if topics_change:
                gh("-X", "PUT", f"repos/{OWNER}/{name}/topics", data={"names": want_topics})
            print("   applied")
    if not apply:
        print("\nDry run. Re-run with --apply to make these changes.")


if __name__ == "__main__":
    main()
