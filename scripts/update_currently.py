#!/usr/bin/env python3
"""Rewrite the "Currently working on" block of README.md from recent commits.

Public repos show up as `name: description`. A private repo shows up only if it
is listed in the CURRENTLY_PRIVATE secret, and then only under the label, blurb
and optional url given there. That secret is the only place private repo names
live; nothing about them is committed to this public repo.

CURRENTLY_PRIVATE is JSON: {"owner/repo": {"label": "...", "blurb": "...", "url": "..."}}
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
MAX_BRANCHES = 30


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
    """Dates of the user's commits since `since` on any branch, deduplicated by sha."""
    try:
        branches = call(f"/repos/{full_name}/branches", token, {"per_page": MAX_BRANCHES})
    except urllib.error.HTTPError:
        return []
    found = {}
    for branch in branches:
        try:
            commits = call(
                f"/repos/{full_name}/commits",
                token,
                {"sha": branch["name"], "author": user, "since": since.isoformat(), "per_page": 100},
            )
        except urllib.error.HTTPError:
            continue  # empty branch or no access
        for c in commits:
            found[c["sha"]] = parse_date(c["commit"]["author"]["date"])
    return list(found.values())


def plain(text):
    """Collapse whitespace and swap dashes for punctuation: ': ' first, then ', '."""
    seen = []

    def swap(_):
        seen.append(1)
        return ": " if len(seen) == 1 else ", "

    return re.sub(r"\s*[—–]\s*", swap, " ".join((text or "").split()))


def blurb(description, limit=110):
    """First sentence of a repo description, capped at a word boundary, HTML-escaped."""
    text = plain(description)
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].rstrip(".")
    if len(first) > limit:
        first = first[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return html.escape(first, quote=False)


def line_for(repo, private):
    if repo["private"]:
        alias = private.get(repo["full_name"])
        if not alias:
            return None
        label = f"**{html.escape(alias['label'], quote=False)}**"
        if alias.get("url"):
            label = f"[{label}]({alias['url']})"
        return f"- {label}: {html.escape(plain(alias['blurb']), quote=False)}"
    text = blurb(repo.get("description"))
    link = f"[**{repo['name']}**]({repo['html_url']})"
    return f"- {link}: {text}" if text else f"- {link}"


def list_repos(user, config):
    """Candidate repos paired with the token that can read each one. Personal tokens win."""
    repos = {}
    public_token = os.environ.get("GITHUB_TOKEN")
    for repo in call(f"/users/{user}/repos", public_token, {"type": "owner", "sort": "pushed", "per_page": 50}):
        repos[repo["full_name"]] = (repo, public_token)
    for name in config["token_env"]:
        token = os.environ.get(name)
        if not token:
            continue
        params = {"affiliation": "owner,collaborator,organization_member", "sort": "pushed", "per_page": 50}
        for repo in call("/user/repos", token, params):
            repos[repo["full_name"]] = (repo, token)
    return list(repos.values())


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    user = os.environ.get("GITHUB_REPOSITORY_OWNER") or config["user"]
    private = json.loads(os.environ.get("CURRENTLY_PRIVATE") or "{}")
    windows = sorted(config["window_days"])
    max_items, min_items = config["max_items"], config["min_items"]
    exclude = set(config["exclude"]) | {f"{user}/{user}"}

    now = datetime.now(timezone.utc)
    widest = now - timedelta(days=windows[-1])

    activity = []
    for repo, token in list_repos(user, config):
        if repo["fork"] or repo["archived"] or repo["full_name"] in exclude:
            continue
        if repo["private"] and repo["full_name"] not in private:
            continue
        if parse_date(repo["pushed_at"]) < widest:
            continue
        dates = commit_dates(repo["full_name"], user, widest, token)
        if dates:
            activity.append((repo, dates))

    ranked = []
    for days in windows:
        cutoff = now - timedelta(days=days)
        ranked = sorted(
            ((sum(d >= cutoff for d in dates), max(dates), repo) for repo, dates in activity),
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        ranked = [item for item in ranked if item[0] > 0]
        if len(ranked) >= min_items:
            break

    lines = [line_for(repo, private) for _, _, repo in ranked[:max_items]]
    lines = [line for line in lines if line]
    if not lines:
        print("No recent activity found; leaving README.md unchanged.")
        return

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    updated = pattern.sub(lambda _: f"{START}\n" + "\n".join(lines) + f"\n{END}", text)
    if updated == text:
        print("README.md already up to date.")
        return
    README.write_text(updated, encoding="utf-8")
    print(f"Updated README.md with {len(lines)} item(s).")


if __name__ == "__main__":
    main()
