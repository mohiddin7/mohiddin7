#!/usr/bin/env python3
"""Draw my contribution calendar for the last year as two SVGs (dark and light).

Same layout as the calendar on a GitHub profile, with the numbers printed on it,
because hover tooltips don't work inside a README image: the yearly total, a count
under each month, the busiest day, the longest and current streaks, and active days.

Data comes from the GraphQL API with the workflow's token. If that fails, it falls
back to the public contributions page. If both fail, the existing SVGs are left alone.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_currently import CONFIG, ROOT  # noqa: E402

ASSETS = ROOT / "assets"
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
THEMES = {
    "dark": {"cells": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"], "text": "#e6edf3", "muted": "#8b949e"},
    "light": {"cells": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"], "text": "#1f2328", "muted": "#656d76"},
}
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
CELL, GAP, LEFT, TOP = 10, 3, 32, 62
STEP = CELL + GAP
# The snake: head first. GitHub blue, a lighter head in dark mode and a deeper one in light mode.
SNAKE = {"dark": ["#79c0ff", "#58a6ff", "#58a6ff", "#388bfd"], "light": ["#0550ae", "#0969da", "#0969da", "#218bff"]}
STEP_SECONDS, PAUSE_SECONDS = 0.09, 3.0


def fetch_graphql(user, token):
    url = os.environ.get("GITHUB_GRAPHQL_URL", "https://api.github.com/graphql")
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "profile-readme-calendar"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=30) as r:
        data = json.load(r)
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        (date.fromisoformat(d["date"]), d["contributionCount"], LEVELS.get(d["contributionLevel"], 0))
        for week in calendar["weeks"]
        for d in week["contributionDays"]
    ]
    return calendar["totalContributions"], days


def fetch_html(user):
    url = os.environ.get("CONTRIBUTIONS_URL") or f"https://github.com/users/{user}/contributions"
    request = urllib.request.Request(url, headers={"User-Agent": "profile-readme-calendar"})
    with urllib.request.urlopen(request, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    counts = {}
    for target, text in re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        number = re.match(r"\s*([\d,]+) contributions?", text)
        counts[target] = int(number.group(1).replace(",", "")) if number else 0
    days = []
    for tag in re.findall(r"<td\b[^>]*\bdata-date=\"[^\"]+\"[^>]*>", page):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        days.append((date.fromisoformat(attrs["data-date"]), counts.get(attrs.get("id"), 0), int(attrs.get("data-level", 0))))
    if not days:
        raise ValueError("no calendar cells found on the contributions page")
    days.sort()
    heading = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", page)
    total = int(heading.group(1).replace(",", "")) if heading else sum(c for _, c, _ in days)
    return total, days


def stats(days):
    """Busiest day, longest and current streaks, active days. Ties for busiest go to the latest day."""
    busiest = max(days, key=lambda d: (d[1], d[0]))
    longest = run = 0
    for _, count, _ in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    current, tail = 0, list(days)
    if tail and tail[-1][1] == 0:  # today may simply not have started yet
        tail.pop()
    for _, count, _ in reversed(tail):
        if not count:
            break
        current += 1
    return {
        "busiest": busiest,
        "longest": longest,
        "current": current,
        "active": sum(1 for _, c, _ in days if c),
        "days": len(days),
    }


def plural(n, word):
    return f"{n:,} {word}" if n == 1 else f"{n:,} {word}s"


def layout(days):
    """Column per week (weeks start on Sunday, like GitHub), and the month labels across the top."""
    start = days[0][0] - timedelta(days=(days[0][0].weekday() + 1) % 7)
    cells = [((d - start).days // 7, (d.weekday() + 1) % 7, d, c, lvl) for d, c, lvl in days]
    month_totals = {}
    for d, c, _ in days:
        month_totals[(d.year, d.month)] = month_totals.get((d.year, d.month), 0) + c
    labels, seen = [], set()
    for col, row, d, _, _ in cells:
        key = (d.year, d.month)
        if key not in seen and (row == 0 or col == 0):
            seen.add(key)
            labels.append((col, d))
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3:  # a sliver of a month at the start would overlap
        labels.pop(0)
    out = []
    for i, (col, d) in enumerate(labels):
        name = d.strftime("%b")
        if i == 0 or d.month == 1:
            name += f" {d.year}"
        out.append((col, name, month_totals[(d.year, d.month)]))
    return cells, out


def snake_path(cells):
    """Walk the grid one cell at a time, sweeping left to right.

    The next goal is the uneaten active cell in the leftmost column, the nearest row first, so
    no cell is left behind for a long trip back. Active cells passed on the way are eaten then
    too. Returns the (column, row) positions and the step at which each active cell is eaten.
    """
    targets = {(col, row) for col, row, _, count, _ in cells if count}
    if not targets:
        return [], {}
    pos = min(targets)
    path, eaten = [pos], {pos: 0}
    targets.discard(pos)
    while targets:
        goal = min(targets, key=lambda t: (t[0], abs(t[1] - pos[1]), t[1]))
        while pos != goal:
            col, row = pos
            if col != goal[0]:
                col += 1 if goal[0] > col else -1
            else:
                row += 1 if goal[1] > row else -1
            pos = (col, row)
            path.append(pos)
            if pos in targets:
                targets.discard(pos)
                eaten[pos] = len(path) - 1
    return path, eaten


def snake_css(path, eaten, cell_index, theme):
    """CSS for the snake's moves and for each active cell turning empty when it is eaten."""
    t = THEMES[theme]
    loop = len(path) * STEP_SECONDS + PAUSE_SECONDS
    pct = lambda step: step * STEP_SECONDS / loop * 100  # noqa: E731
    frames = "".join(
        f"{pct(i):.3f}%{{transform:translate({LEFT + c * STEP}px,{TOP + r * STEP}px)}}" for i, (c, r) in enumerate(path)
    )
    last_c, last_r = path[-1]
    rules = [
        f"@keyframes sn{{{frames}100%{{transform:translate({LEFT + last_c * STEP}px,{TOP + last_r * STEP}px)}}}}",
        f".sn rect{{animation:sn {loop:.2f}s linear infinite backwards}}",
    ]
    for k in range(1, len(SNAKE[theme])):
        rules.append(f".sn .s{k}{{animation-delay:{k * STEP_SECONDS:.2f}s}}")
    for pos, step in sorted(eaten.items(), key=lambda item: item[1]):
        i, level = cell_index[pos]
        at = pct(step)
        rules.append(
            f"@keyframes e{i}{{0%,{at:.3f}%{{fill:{t['cells'][level]}}}{at + 0.001:.3f}%,100%{{fill:{t['cells'][0]}}}}}"
            f".e{i}{{animation:e{i} {loop:.2f}s linear infinite}}"
        )
    rules.append("@media (prefers-reduced-motion: reduce){*{animation:none!important}.sn{display:none}}")
    return "".join(rules)


def svg(total, days, theme):
    t = THEMES[theme]
    s = stats(days)
    cells, months = layout(days)
    path, eaten = snake_path(cells)
    cell_index = {(col, row): (i, level) for i, (col, row, _, _, level) in enumerate(cells)}
    columns = max(c for c, *_ in cells) + 1
    width = LEFT + columns * STEP + 8
    grid_bottom = TOP + 7 * STEP
    height = grid_bottom + 46
    b_day, b_count = s["busiest"][0], s["busiest"][1]
    summary = (
        f"{plural(total, 'contribution')} in the last year. Busiest day: {b_day:%b} {b_day.day}, {b_day.year} "
        f"({b_count}). Longest streak: {plural(s['longest'], 'day')}. Current streak: {plural(s['current'], 'day')}. "
        f"Active days: {s['active']} of {s['days']}."
    )
    e = lambda text: html.escape(text, quote=True)  # noqa: E731
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{e(summary)}"><title>{e(summary)}</title>',
        f"<style>{snake_css(path, eaten, cell_index, theme)}</style>" if path else "",
        f'<g font-family="{FONT}">',
        f'<text x="{LEFT}" y="18" font-size="14" font-weight="600" fill="{t["text"]}">'
        f"{e(plural(total, 'contribution'))} in the last year</text>",
    ]
    for col, name, count in months:
        x = LEFT + col * STEP
        parts.append(f'<text x="{x}" y="40" font-size="10" fill="{t["text"]}">{e(name)}</text>')
        parts.append(f'<text x="{x}" y="52" font-size="9" fill="{t["muted"]}">{count:,}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="0" y="{TOP + row * STEP + 9}" font-size="10" fill="{t["muted"]}">{name}</text>')
    for i, (col, row, d, count, level) in enumerate(cells):
        css = f' class="e{i}"' if (col, row) in eaten else ""
        parts.append(
            f'<rect{css} x="{LEFT + col * STEP}" y="{TOP + row * STEP}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{t["cells"][level]}"><title>{e(plural(count, "contribution"))} on {d:%b} {d.day}, {d.year}</title></rect>'
        )
    if path:  # the snake, drawn over the cells; each segment is one step behind the one in front
        parts.append('<g class="sn">')
        for k, color in reversed(list(enumerate(SNAKE[theme]))):
            size = CELL - k
            parts.append(
                f'<rect class="s{k}" x="{k / 2}" y="{k / 2}" width="{size}" height="{size}" rx="{3 if k == 0 else 2.5}" '
                f'fill="{color}"/>'
            )
        parts.append("</g>")
    # Legend on its own row at the bottom right, like GitHub's: Less [5 swatches] More
    legend_y = grid_bottom + 6
    more_x = LEFT + columns * STEP - 26
    swatch_x = more_x - 4 - 5 * STEP + GAP
    parts.append(
        f'<text x="{swatch_x - 4}" y="{legend_y + 9}" font-size="10" text-anchor="end" fill="{t["muted"]}">Less</text>'
    )
    for i, color in enumerate(t["cells"]):
        parts.append(
            f'<rect x="{swatch_x + i * STEP}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>'
        )
    parts.append(f'<text x="{more_x}" y="{legend_y + 9}" font-size="10" fill="{t["muted"]}">More</text>')
    line = (
        f"Busiest day: {b_day:%b} {b_day.day}, {b_day.year} ({b_count:,})  ·  "
        f"Longest streak: {plural(s['longest'], 'day')}  ·  Current streak: {plural(s['current'], 'day')}  ·  "
        f"Active days: {s['active']} of {s['days']}"
    )
    parts.append(f'<text x="{LEFT}" y="{legend_y + 32}" font-size="11" fill="{t["text"]}">{e(line)}</text>')
    parts.append("</g></svg>\n")
    return "".join(parts)


def main():
    user = os.environ.get("GITHUB_REPOSITORY_OWNER") or json.loads(CONFIG.read_text(encoding="utf-8"))["user"]
    try:
        total, days = fetch_graphql(user, os.environ.get("GITHUB_TOKEN"))
        source = "GraphQL"
    except (urllib.error.URLError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"GraphQL failed ({type(error).__name__}); trying the public contributions page.")
        try:
            total, days = fetch_html(user)
            source = "contributions page"
        except (urllib.error.URLError, OSError, KeyError, ValueError) as error2:
            sys.exit(f"Could not read the contribution calendar ({type(error2).__name__}); SVGs left as they were.")
    ASSETS.mkdir(exist_ok=True)
    changed = False
    for theme in THEMES:
        path = ASSETS / f"calendar-{theme}.svg"
        new = svg(total, days, theme)
        if not path.exists() or path.read_text(encoding="utf-8") != new:
            path.write_text(new, encoding="utf-8")
            changed = True
    print(f"Calendar from {source}: {total} contributions over {len(days)} days ({'updated' if changed else 'unchanged'}).")


if __name__ == "__main__":
    main()
