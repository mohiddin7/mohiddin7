#!/usr/bin/env python3
"""Rebuild the "Building right now" cards in README.md from recent commits.

Every repo the tokens can read counts: public and private, personal and org,
every branch. Each project gets a card (scripts/now_cards.py) with what it is,
whether it is active, its latest commit, its language and a bar chart of my
commits over the ranking window. Cards link to the project when it has a link.

Public repos show up under their name and description. A private repo listed in
the CURRENTLY_PRIVATE secret shows up under the label, blurb and optional url
given there. Any other active private repo is folded into one anonymous "under
wraps" card with only its language and commit counts. That secret is the only place
private repo names live; nothing about them is committed to this public repo.

CURRENTLY_PRIVATE is JSON:
  {"owner/repo": {"label": "...", "blurb": "...", "url": "...", "commits": false}}
  {"owner/repo": {"hide": true}}   # never mention it, not even under wraps
"commits": true also shows that private repo's latest commit message.
"""
import hashlib
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from now_cards import BARS, THEMES, card  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CONFIG = ROOT / "config" / "currently.json"
ASSETS = ROOT / "assets"
RAW = "https://raw.githubusercontent.com/{repo}/{branch}/assets/{file}?v={version}"
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
    """First sentence of a repo description, capped at a word boundary."""
    text = plain(description)
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0].rstrip(".")
    if len(first) > limit:
        first = first[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return first


# Commit subjects that say nothing about the work, or that I'd rather not print.
SKIP_SUBJECT = re.compile(r"^(merge|wip\b|revert \"merge)|co-authored|claude", re.I)


def subject(commits):
    """The newest commit worth quoting, as (subject, commit), or (None, None)."""
    for c in commits:
        text = plain(c["subject"])
        if c["merge"] or not text or SKIP_SUBJECT.search(text):
            continue
        return text, c
    return None, None


def span(days):
    if days % 30 == 0:
        n, unit = days // 30, "month"
    elif days % 7 == 0:
        n, unit = days // 7, "week"
    else:
        n, unit = days, "day"
    return f"last {unit}" if n == 1 else f"last {n} {unit}s"


def age(moment, today, tz):
    return (today - moment.astimezone(tz).date()).days


def when(moment, today, tz):
    days = age(moment, today, tz)
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    return f"{days // 30} months ago"


def status(moment, today, tz):
    days = age(moment, today, tz)
    return "active" if days < 7 else "recent" if days < 30 else "resting"


def buckets(commits, days, now):
    """Commit counts over the window in BARS equal slices, oldest first."""
    counts = [0] * BARS
    size = days / BARS
    for c in commits:
        back = (now - c["date"]).total_seconds() / 86400
        if 0 <= back < days:
            counts[BARS - 1 - int(back / size)] += 1
    return counts


def item_for(repo, commits, count, days, private, now, today, tz):
    latest = commits[0]["date"]
    base = {
        "language": repo.get("language"),
        "count": count,
        "span": span(days),
        "when": when(latest, today, tz),
        "status": status(latest, today, tz),
        "buckets": buckets(commits, days, now),
        "message": None,
    }
    if repo["private"]:
        alias = private[repo["full_name"]]
        base.update(name=plain(alias["label"]), blurb=plain(alias["blurb"]), url=alias.get("url"))
        show = alias.get("commits")
    else:
        base.update(name=repo["name"], blurb=blurb(repo.get("description")), url=repo["html_url"])
        show = True
    if show:
        text, commit = subject(commits)
        if text:
            base.update(message=text, when=when(commit["date"], today, tz))
    return base


def under_wraps(items, days, now, today, tz):
    """One anonymous card for active private repos that have no public name yet."""
    if not items:
        return None
    commits = sorted((c for _, _, cs in items for c in cs), key=lambda c: c["date"], reverse=True)
    languages = sorted({repo["language"] for _, repo, _ in items if repo.get("language")})
    return {
        "name": "Something under wraps" if len(items) == 1 else f"{len(items)} things under wraps",
        "blurb": "No name yet, no screenshots, just commits.",
        "url": None,
        "wraps": True,
        "language": ", ".join(languages) or None,
        "count": sum(count for count, _, _ in items),
        "span": span(days),
        "when": when(commits[0]["date"], today, tz),
        "status": status(commits[0]["date"], today, tz),
        "buckets": buckets(commits, days, now),
        "message": None,
    }


def alt(item):
    """Alt text carries everything the card shows, for screen readers and search engines."""
    text = f"{item['name']}: {item['blurb']} {item['count']} commits in the {item['span']}, latest {item['when']}"
    if item.get("message"):
        text += f": {item['message']}"
    if item.get("language"):
        text += f". {item['language']}"
    return html.escape(text, quote=True)


def write_cards(items, day_label):
    """Write assets/now-N-{theme}.svg, drop leftovers from a longer list, return the README block."""
    repo = os.environ.get("GITHUB_REPOSITORY") or "mohiddin7/mohiddin7"
    branch = os.environ.get("WORKLOG_BRANCH") or os.environ.get("GITHUB_REF_NAME") or "main"
    ASSETS.mkdir(exist_ok=True)
    keep, rows = set(), []
    for n, item in enumerate(items, 1):
        urls = {}
        for theme in THEMES:
            name = f"now-{n}-{theme}.svg"
            body = card(item, theme)
            (ASSETS / name).write_text(body, encoding="utf-8")
            keep.add(name)
            version = hashlib.sha256(body.encode()).hexdigest()[:10]
            urls[theme] = RAW.format(repo=repo, branch=branch, file=name, version=version)
        picture = (
            "<picture>"
            f'<source media="(prefers-color-scheme: dark)" srcset="{urls["dark"]}" />'
            f'<source media="(prefers-color-scheme: light)" srcset="{urls["light"]}" />'
            f'<img src="{urls["light"]}" width="100%" alt="{alt(item)}" />'
            "</picture>"
        )
        rows.append(f'<a href="{html.escape(item["url"], quote=True)}">{picture}</a>' if item.get("url") else picture)
    for old in ASSETS.glob("now-*.svg"):
        if old.name not in keep:
            old.unlink()
    caption = (
        f"<sub>Updated {day_label} from my commits on every branch of my personal and org repos, private ones included. "
        "Bars are commits over the window. I don't touch this; a workflow does.</sub>"
    )
    return "\n".join(rows + ["", caption])


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

    items = [item_for(repo, commits, count, days, private, now, today, tz) for count, _, repo, commits, _ in named[:max_items]]
    wraps = under_wraps([(count, repo, commits) for count, _, repo, commits, w in ranked if w], days, now, today, tz)
    if wraps:
        items.append(wraps)
    if not items:
        print("No recent activity found; leaving README.md unchanged.")
        return

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    block = write_cards(items, f"{today:%b} {today.day}, {today.year}")
    updated = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    if updated == text:
        print("README.md already up to date.")
        return
    README.write_text(updated, encoding="utf-8")
    print(f"Updated README.md with {len(items)} card(s).")


if __name__ == "__main__":
    main()
