#!/usr/bin/env python3
"""Rewrite the greeting at the top of README.md for my time of day and the visitor's theme.

A README can't see its visitor, so the greeting changes with my clock instead
(morning, afternoon, evening, night) and ships two versions: one for GitHub's
dark theme and one for light. Each version is a small SVG that a <picture>
picks with prefers-color-scheme.

Lines come from the getmeme API. Anything unusable (no key, an HTTP error, a
null answer, a line that fails the checks below) falls back to a hand-written
line for the same daypart and theme, so the greeting is never empty. The API
is only called when the daypart changes.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_currently import README, ROOT, plain  # noqa: E402

ASSETS = ROOT / "assets"
RAW = "https://raw.githubusercontent.com/{repo}/{branch}/assets/greeting-{theme}.svg?v={version}"
START_RE = re.compile(r"<!-- GREETING:START(?: daypart=(\w+) date=([\d-]+))? -->")
END = "<!-- GREETING:END -->"
DEFAULT_URL = "https://getmeme.warmhop.com"
MAX_LENGTH = 90
SAFE = re.compile(r"^[A-Za-z0-9 ,.'!?:;()\"&%+/-]+$")
FORBID = ["claude", "anthropic", "openai", "hire", "hiring", "job", "resume", "email", "linkedin", "recruit"]
THEMES = ("dark", "light")
COLORS = {"dark": "#c9d1d9", "light": "#1f2328"}
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
INFO = (
    '<a href="#how-this-page-works" title="Written by getmeme for my time of day and your GitHub theme">ⓘ</a>'
)

SYSTEM = (
    "You write one short, friendly greeting for the top of a software engineer's GitHub profile page. "
    "The visitor is a developer or a recruiter who is skimming. Use plain everyday words and dry, light "
    "developer humor. Do not name the engineer, any company or any product, and never mention hiring or jobs. "
    "One or two short sentences."
)
SCENE = {
    "morning": "it is morning and the coffee is still kicking in",
    "afternoon": "it is the middle of the afternoon",
    "evening": "it is evening and the side projects come out",
    "night": "it is late at night and they are probably still coding",
}

FALLBACKS = {
    ("morning", "dark"): [
        "Morning here. You're in dark mode already? Respect, night owl.",
        "Good morning. My coffee is loading, your dark theme is not.",
        "It's morning on my side. The terminal and I are both still waking up.",
    ],
    ("morning", "light"): [
        "Good morning. Light mode and sunrise, you're having a bright day.",
        "Morning here. Bold of you to read this in light mode.",
        "It's morning for me. Coffee in one hand, logs in the other.",
    ],
    ("afternoon", "dark"): [
        "Afternoon here. Peak productivity, or peak snack time. Same thing.",
        "Good afternoon. Dark mode at lunch, I like your style.",
        "It's afternoon on my side. The bugs have had their lunch too.",
    ],
    ("afternoon", "light"): [
        "Good afternoon. Light mode in daylight, very sensible of you.",
        "Afternoon here. If I'm quiet, I'm in a meeting about meetings.",
        "It's afternoon for me. The evals are running, and so am I.",
    ],
    ("evening", "dark"): [
        "Evening here. Dark mode, low lights, perfect time to read code.",
        "Good evening. This is when the side projects come out.",
        "It's evening on my side. The models are calm, mostly.",
    ],
    ("evening", "light"): [
        "Good evening. Still in light mode? Your eyes are braver than mine.",
        "Evening here. I should stop coding. I won't.",
        "It's evening for me. Shipping small things before dinner.",
    ],
    ("night", "dark"): [
        "It's late here. If I'm online, a model is winning an argument.",
        "Night mode on both ends. Welcome, fellow owl.",
        "Good night from my side. Any commit after midnight is under review.",
    ],
    ("night", "light"): [
        "It's late night here, and you brought light mode. Bold.",
        "Late night on my side. The evals are asleep, I am not.",
        "Night here. Please lower your screen brightness on my behalf.",
    ],
}


def daypart(local):
    hour = local.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def day_key(local):
    """Calendar date of the daypart. Shifted 5 hours so one night (22:00 to 05:00) is a single key."""
    return (local - timedelta(hours=5)).date().isoformat()


def clean(text):
    """Return a safe single line, or None if the text should not be published."""
    if not isinstance(text, str):
        return None
    quotes = {"‘": "'", "’": "'", "“": '"', "”": '"'}
    text = " ".join(plain(text).translate(str.maketrans(quotes)).split())
    if not 10 <= len(text) <= MAX_LENGTH + 10 or not SAFE.match(text):
        return None
    if re.search(r"https?:|www\.|\.com|\.io|@", text, re.I):
        return None
    return text


def ask(base_url, key, part, theme, seed):
    body = json.dumps(
        {
            "system": SYSTEM,
            "prompt": (
                f"Greet the visitor. On the engineer's side {SCENE[part]}. "
                f"The visitor is reading the page in {theme} mode. Joke about either, or both. Seed {seed}."
            ),
            "maxLength": MAX_LENGTH,
            "forbid": FORBID,
            "timeoutMs": 20000,
        }
    ).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v1/lines",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "profile-readme-greeting",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        print(f"{theme}: getmeme answered HTTP {error.code}; using a fallback line.")
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        print(f"{theme}: getmeme unreachable ({type(error).__name__}); using a fallback line.")
        return None
    if not isinstance(data, dict) or not data.get("text"):
        reason = data.get("reason") if isinstance(data, dict) else None
        print(f"{theme}: getmeme returned no line (reason: {reason}); using a fallback line.")
        return None
    return data["text"]


def svg(line, theme):
    text = html.escape(line, quote=True)
    width = max(240, int(len(line) * 8.2) + 24)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="30" viewBox="0 0 {width} 30" '
        f'role="img" aria-label="{text}"><title>{text}</title>'
        f'<text x="50%" y="20" text-anchor="middle" font-family="{FONT}" font-size="15" '
        f'font-style="italic" fill="{COLORS[theme]}">{text}</text></svg>\n'
    )


def main():
    zone = ZoneInfo(os.environ.get("GREETING_TZ") or "America/New_York")
    now = datetime.now(timezone.utc)
    if os.environ.get("GREETING_NOW"):  # tests only
        now = datetime.fromisoformat(os.environ["GREETING_NOW"])
    local = now.astimezone(zone)
    part, date = daypart(local), day_key(local)

    text = README.read_text(encoding="utf-8")
    start = START_RE.search(text)
    if not start or END not in text[start.end():]:
        sys.exit("Markers <!-- GREETING:START --> / <!-- GREETING:END --> not found in README.md")
    if start.group(1) == part and start.group(2) == date:
        print(f"Greeting already set for {date} {part}.")
        return

    key = os.environ.get("GETMEME_API_KEY")
    base_url = os.environ.get("GETMEME_URL") or DEFAULT_URL
    seed = local.timetuple().tm_yday
    lines, sources = {}, {}
    for theme in THEMES:
        line = clean(ask(base_url, key, part, theme, seed)) if key else None
        sources[theme] = "getmeme" if line else "fallback"
        pool = FALLBACKS[(part, theme)]
        lines[theme] = line or pool[seed % len(pool)]

    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        (ASSETS / f"greeting-{theme}.svg").write_text(svg(lines[theme], theme), encoding="utf-8")

    repo = os.environ.get("GITHUB_REPOSITORY") or "mohiddin7/mohiddin7"
    branch = os.environ.get("GREETING_BRANCH") or os.environ.get("GITHUB_REF_NAME") or "main"
    url = {t: RAW.format(repo=repo, branch=branch, theme=t, version=f"{date}-{part}") for t in THEMES}
    block = "\n".join(
        [
            f"<!-- GREETING:START daypart={part} date={date} -->",
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="{url["dark"]}" />',
            f'  <source media="(prefers-color-scheme: light)" srcset="{url["light"]}" />',
            f'  <img src="{url["light"]}" alt="{html.escape(lines["light"], quote=True)}" />',
            "</picture>",
            INFO,
            END,
        ]
    )
    end = text.index(END, start.end()) + len(END)
    README.write_text(text[: start.start()] + block + text[end:], encoding="utf-8")
    print(f"Greeting set for {date} {part} (dark: {sources['dark']}, light: {sources['light']}).")


if __name__ == "__main__":
    main()
