#!/usr/bin/env python3
"""Rewrite the "Currently working on" block of README.md from recent commits.

Every repo the tokens can read counts: public and private, personal and org,
every branch. Each line says what the project is, how busy it has been, when I
last committed and, for public repos, what that commit was.

Public repos show up as `name: description`. A private repo listed in the
CURRENTLY_PRIVATE secret shows up under the label, blurb and optional url given
there. Any other active private repo is folded into one anonymous "under wraps"
line with only its language and commit counts. That secret is the only place
private repo names live; nothing about them is committed to this public repo.

CURRENTLY_PRIVATE is JSON:
  {"owner/repo": {"label": "...", "blurb": "...", "url": "...", "commits": false}}
  {"owner/repo": {"hide": true}}   # never mention it, not even under wraps
"commits": true also shows that private repo's latest commit message.
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
from zoneinfo import ZoneInfo

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


def recent_commits(full_name, user, since, token):
    """The user's commits since `since` on any branch, deduplicated by sha, newest first."""
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
            found[c["sha"]] = {
                "date": parse_date(c["commit"]["author"]["date"]),
                "subject": (c["commit"].get("message") or "").split("\n", 1)[0],
                "merge": len(c.get("parents") or []) > 1,
            }
    return sorted(found.values(), key=lambda c: c["date"], reverse=True)


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


# Commit subjects that say nothing about the work, or that I'd rather not print.
SKIP_SUBJECT = re.compile(r"^(merge|wip\b|revert \"merge)|co-authored|claude", re.I)


def subject(commits, limit=72):
    """The newest commit subject worth printing, trimmed at a word boundary, and its commit."""
    for c in commits:
        text = plain(c["subject"])
        if c["merge"] or not text or SKIP_SUBJECT.search(text):
            continue
        if len(text) > limit:
            text = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
        return html.escape(text, quote=False), c
    return None, None


def span(days):
    if days % 30 == 0:
        n, unit = days // 30, "month"
    elif days % 7 == 0:
        n, unit = days // 7, "week"
    else:
        n, unit = days, "day"
    return f"the last {unit}" if n == 1 else f"the last {n} {unit}s"


def when(moment, today, tz):
    days = (today - moment.astimezone(tz).date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def dot(moment, today, tz):
    days = (today - moment.astimezone(tz).date()).days
    return "🟢" if days < 7 else "🟡" if days < 30 else "⚪"


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def stats(languages, count, days, latest, today, tz, message=None):
    """`message` is (subject, commit); its own date is used so the two never disagree."""
    parts = [", ".join(languages)] if languages else []
    parts.append(f"{plural(count, 'commit')} in {span(days)}")
    text, commit = message or (None, None)
    if text:
        parts.append(f"latest {when(commit['date'], today, tz)}: <code>{text}</code>")
    else:
        parts.append(f"latest {when(latest, today, tz)}")
    return "<br/><sub>" + " · ".join(parts) + "</sub>"


def line_for(repo, commits, count, days, private, today, tz):
    latest = commits[0]["date"]
    languages = [repo["language"]] if repo.get("language") else []
    if repo["private"]:
        alias = private[repo["full_name"]]
        label = f"**{html.escape(alias['label'], quote=False)}**"
        if alias.get("url"):
            label = f"[{label}]({alias['url']})"
        text = html.escape(plain(alias["blurb"]), quote=False)
        message = subject(commits) if alias.get("commits") else None
    else:
        label = f"[**{repo['name']}**]({repo['html_url']})"
        text = blurb(repo.get("description"))
        message = subject(commits)
    head = f"- {dot(latest, today, tz)} {label}" + (f": {text}" if text else "")
    return head + stats(languages, count, days, latest, today, tz, message)


def under_wraps(items, days, today, tz):
    """One anonymous line for active private repos that have no public name yet."""
    if not items:
        return None
    count = sum(c for c, _, _, _ in items)
    latest = max(commits[0]["date"] for _, _, _, commits in items)
    languages = sorted({repo["language"] for _, _, repo, _ in items if repo.get("language")})
    what = "Something under wraps" if len(items) == 1 else f"{len(items)} things under wraps"
    text = "no name yet, no screenshots, just commits"
    return f"- 🔒 **{what}**: {text}" + stats(languages, count, days, latest, today, tz)


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
    tz = ZoneInfo(os.environ.get("GREETING_TZ") or config.get("tz") or "America/New_York")
    windows = sorted(config["window_days"])
    max_items, min_items = config["max_items"], config["min_items"]
    exclude = set(config["exclude"]) | {f"{user}/{user}"}
    show_wraps = config.get("under_wraps", True)

    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    widest = now - timedelta(days=windows[-1])

    activity = []
    for repo, token in list_repos(user, config):
        if repo["fork"] or repo["archived"] or repo["full_name"] in exclude:
            continue
        alias = private.get(repo["full_name"]) or {}
        if repo["private"] and (alias.get("hide") or (not alias.get("label") and not show_wraps)):
            continue
        if parse_date(repo["pushed_at"]) < widest:
            continue
        commits = recent_commits(repo["full_name"], user, widest, token)
        if commits:
            activity.append((repo, commits, bool(repo["private"] and not alias.get("label"))))

    for days in windows:
        cutoff = now - timedelta(days=days)
        ranked = sorted(
            (
                (sum(c["date"] >= cutoff for c in commits), commits[0]["date"], repo, commits, wraps)
                for repo, commits, wraps in activity
            ),
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        ranked = [item for item in ranked if item[0] > 0]
        named = [item for item in ranked if not item[4]]
        if len(named) >= min_items:
            break

    lines = [line_for(repo, commits, count, days, private, today, tz) for count, _, repo, commits, _ in named[:max_items]]
    wraps = under_wraps([(c, d, r, cm) for c, d, r, cm, w in ranked if w], days, today, tz)
    if wraps:
        lines.append(wraps)
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
