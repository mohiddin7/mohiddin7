#!/usr/bin/env python3
"""Rewrite the greeting line at the top of README.md.

Asks the getmeme API for one short line. Anything unusable (no key, an HTTP
error, a null answer, a line that fails the checks below) falls back to a
hand-written line picked by day of year, so the block is never empty.
"""
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_currently import README, plain  # noqa: E402

START, END = "<!-- GREETING:START -->", "<!-- GREETING:END -->"
DEFAULT_URL = "https://getmeme.warmhop.com"
MAX_LENGTH = 90
SAFE = re.compile(r"^[A-Za-z0-9 ,.'!?:;()\"&%+/-]+$")
FORBID = ["claude", "anthropic", "openai", "hire", "hiring", "job", "resume", "email", "linkedin", "recruit"]

SYSTEM = (
    "You write one short, friendly greeting for the top of a software engineer's GitHub profile page. "
    "The visitor is a developer or a recruiter who is skimming. Use plain everyday words and dry, light "
    "developer humor. Do not name the engineer, any company or any product, and never mention hiring or jobs. "
    "One or two short sentences."
)

FALLBACKS = [
    "Welcome. The coffee is imaginary but the code is real.",
    "Hi there. Please ignore the TODOs, they are load bearing.",
    "You made it. Most of my repos are still compiling.",
    "Hello, human. My linter has already judged you kindly.",
    "Welcome in. Everything here passed its evals, mostly.",
    "Hey. Nothing on this page was deployed on a Friday.",
    "Come on in. The agents are supervised, I promise.",
    "Hi. If something looks broken, it is a feature in review.",
    "Welcome. Scroll gently, the snake is hungry.",
    "Hello. The bugs here are hand made and locally sourced.",
    "Hi, visitor. Tabs or spaces, I will not ask.",
    "Hey there. My prompts are polite and my guardrails are not.",
    "Welcome. Yes, I read the error message. Eventually.",
    "Hello. This page has fewer lines than my last PR description.",
]


def clean(text):
    """Return a safe single line, or None if the text should not be published."""
    if not isinstance(text, str):
        return None
    text = plain(text).translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'}))
    text = " ".join(text.split())
    if not 10 <= len(text) <= MAX_LENGTH + 10 or not SAFE.match(text):
        return None
    if re.search(r"https?:|www\.|\.com|\.io|@", text, re.I):
        return None
    return text


def ask(base_url, key, now):
    body = json.dumps(
        {
            "system": SYSTEM,
            "prompt": f"Greet the visitor. Today is {now:%A}. Pick a fresh angle, seed {now.timetuple().tm_yday}.",
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
        print(f"getmeme answered HTTP {error.code}; using a fallback line.")
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        print(f"getmeme unreachable ({type(error).__name__}); using a fallback line.")
        return None
    if not isinstance(data, dict) or not data.get("text"):
        reason = data.get("reason") if isinstance(data, dict) else None
        print(f"getmeme returned no line (reason: {reason}); using a fallback line.")
        return None
    return data["text"]


def main():
    now = datetime.now(timezone.utc)
    key = os.environ.get("GETMEME_API_KEY")
    base_url = os.environ.get("GETMEME_URL") or DEFAULT_URL

    line = clean(ask(base_url, key, now)) if key else None
    if key and line is None:
        print("The line failed the safety checks or was missing; using a fallback line.")
    source = "getmeme" if line else "fallback"
    line = line or FALLBACKS[now.timetuple().tm_yday % len(FALLBACKS)]

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    block = f"{START}\n<i>{html.escape(line, quote=False)}</i>\n{END}"
    updated = pattern.sub(lambda _: block, text)
    if updated == text:
        print("Greeting already up to date.")
        return
    README.write_text(updated, encoding="utf-8")
    print(f"Greeting updated from {source}.")


if __name__ == "__main__":
    main()
