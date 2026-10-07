#!/usr/bin/env python3
"""Rewrite the "Currently working on" block of README.md from recent commits.

Public repos are listed as `name: description`. A private repo is listed only
if it is allowlisted in config/currently.json, and then only under the label and
blurb written there. Its real name, description and commit messages are never
published.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CONFIG = ROOT / "config" / "currently.json"
START, END = "<!-- CURRENTLY:START -->", "<!-- CURRENTLY:END -->"
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def call(path, token, params=None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-readme-updater",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def parse_date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def commit_dates(full_name, user, since, token):
    """Dates of the user's commits to a repo since `since`; [] if unreadable or empty."""
    try:
        commits = call(
            f"/repos/{full_name}/commits",
            token,
            {"author": user, "since": since.isoformat(), "per_page": 100},
        )
    except urllib.error.HTTPError:
        return []
    return [parse_date(c["commit"]["author"]["date"]) for c in commits]


def blurb(description, limit=110):
    """First sentence of a repo description, capped, HTML-escaped."""
    text = " ".join((description or "").split())
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].rstrip(".")
    if len(first) > limit:
        first = first[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-—") + "…"
    return html.escape(first, quote=False)


def line_for(repo, private_allowlist):
    if repo["private"]:
        alias = private_allowlist.get(repo["full_name"])
        if not alias:
            return None
        return f"- **{html.escape(alias['label'], quote=False)}**: {html.escape(alias['blurb'], quote=False)}"
    text = blurb(repo.get("description"))
    link = f"[**{repo['name']}**]({repo['html_url']})"
    return f"- {link}: {text}" if text else f"- {link}"


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    user = os.environ.get("GITHUB_REPOSITORY_OWNER") or config["user"]
    pat = os.environ.get("PROFILE_READ_TOKEN")
    token = pat or os.environ.get("GITHUB_TOKEN")
    windows = config["window_days"]
    max_items, min_items = config["max_items"], config["min_items"]
    exclude = set(config["exclude"]) | {f"{user}/{user}"}
    private_allowlist = config["private_allowlist"]

    now = datetime.now(timezone.utc)
    widest = now - timedelta(days=max(windows))

    # The Actions token can only see public repos; a personal token also sees private ones.
    if pat:
        repos = call("/user/repos", token, {"affiliation": "owner", "sort": "pushed", "per_page": 50})
    else:
        repos = call(f"/users/{user}/repos", token, {"type": "owner", "sort": "pushed", "per_page": 50})

    activity = []
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["full_name"] in exclude:
            continue
        if repo["private"] and repo["full_name"] not in private_allowlist:
            continue
        if parse_date(repo["pushed_at"]) < widest:
            continue
        dates = commit_dates(repo["full_name"], user, widest, token)
        if dates:
            activity.append((repo, dates))

    ranked = []
    for days in sorted(windows):
        cutoff = now - timedelta(days=days)
        ranked = sorted(
            ((sum(d >= cutoff for d in dates), max(dates), repo) for repo, dates in activity),
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        ranked = [item for item in ranked if item[0] > 0]
        if len(ranked) >= min_items:
            break

    lines = [line_for(repo, private_allowlist) for _, _, repo in ranked[:max_items]]
    lines = [line for line in lines if line]
    if not lines:
        print("No recent activity found; leaving README.md unchanged.")
        return

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    block = "\n".join(lines)
    updated = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    if updated == text:
        print("README.md already up to date.")
        return
    README.write_text(updated, encoding="utf-8")
    print(f"Updated README.md with {len(lines)} item(s).")


if __name__ == "__main__":
    main()
