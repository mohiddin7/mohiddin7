"""Draw the "Building right now" cards: one SVG per project, per GitHub theme.

Pure rendering. update_currently.py gathers the data and decides what goes in.
Each card is 840 x 104: a status bar and name on the left, the latest commit
under it, and on the right the language plus a bar chart of recent commits.
"""
from xml.sax.saxutils import escape

FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,monospace"
W, H = 840, 104
BARS = 14

THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "text": "#e6edf3", "muted": "#8b949e", "code": "#c9d1d9",
        "chip": "#161b22", "empty": "#21262d",
        "status": {"active": "#3fb950", "recent": "#d29922", "resting": "#6e7681"},
        "bars": ["#0e4429", "#006d32", "#26a641", "#39d353"],
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e", "code": "#1f2328",
        "chip": "#f6f8fa", "empty": "#ebedf0",
        "status": {"active": "#1a7f37", "recent": "#9a6700", "resting": "#8c959f"},
        "bars": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
}
STATUS_WORD = {"active": "ACTIVE", "recent": "THIS MONTH", "resting": "RESTING"}

# GitHub's own language colors, for the few languages I actually use.
LANGUAGE_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Go": "#00ADD8",
    "Jupyter Notebook": "#DA5B0B", "HTML": "#e34c26", "CSS": "#563d7c", "R": "#198CE7",
    "Shell": "#89e051", "SQL": "#e38c00", "Rust": "#dea584", "Java": "#b07219",
}


# Rough advance widths (in em) for a GitHub-style sans font, enough to place things after text.
NARROW, WIDE = set("ijlt.,:;'|!()[] fIr"), set("mwMW@%")


def text_width(text, size, bold=False):
    em = 0.0
    for ch in text:
        if ch in NARROW:
            em += 0.3
        elif ch in WIDE:
            em += 0.86
        elif ch.isupper():
            em += 0.67
        elif ch.isdigit():
            em += 0.57
        else:
            em += 0.55
    return em * size * (1.06 if bold else 1.0)


def fit(text, limit):
    """Cut at a word boundary so the line stays inside the card."""
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"


def bars(buckets, t, x, y, height=34):
    """A small column chart; the tallest bucket fills the height, empty buckets show as a stub."""
    top = max(buckets) or 1
    width, gap = 9, 3
    parts = []
    for i, n in enumerate(buckets):
        bx = x + i * (width + gap)
        if n == 0:
            parts.append(f'<rect x="{bx}" y="{y + height - 3}" width="{width}" height="3" rx="1.5" fill="{t["empty"]}"/>')
            continue
        h = max(5, round(height * n / top))
        level = min(3, int(4 * n / top - 1e-9)) if top else 0
        parts.append(
            f'<rect x="{bx}" y="{y + height - h}" width="{width}" height="{h}" rx="2" fill="{t["bars"][level]}">'
            f"<title>{n} commit{'s' if n != 1 else ''}</title></rect>"
        )
    return "".join(parts)


def card(item, theme):
    """item: name, blurb, language, count, span, when, message, status, buckets, wraps."""
    t = THEMES[theme]
    color = t["status"][item["status"]]
    pulse = item["status"] == "active"
    name = escape(fit(item["name"], 40))
    blurb = escape(fit(item["blurb"], 86))
    if item.get("message"):
        latest = f'latest commit {item["when"]}: <tspan fill="{t["code"]}">{escape(fit(item["message"], 56))}</tspan>'
    elif item.get("wraps"):
        latest = f"latest commit {item['when']} · details when it launches"
    else:
        latest = f"latest commit {item['when']} · private repo"
    language = item.get("language")
    chart_x = W - 24 - (BARS * 12 - 3)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f"<title>{name}: {blurb}</title>",
        "<style>",
        "@keyframes pulse{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.6);opacity:0}}",
        ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 1.8s ease-out infinite}",
        "@media (prefers-reduced-motion: reduce){.pulse{animation:none;opacity:0}}",
        "</style>",
        f'<rect x="0.5" y="4.5" width="{W - 1}" height="{H - 9}" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>',
        f'<rect x="0.5" y="4.5" width="5" height="{H - 9}" rx="2.5" fill="{color}"/>',
        f'<g font-family="{FONT}">',
    ]
    # status pill
    if item.get("wraps"):
        out.append(f'<text x="24" y="38" font-size="17" font-weight="600" fill="{t["text"]}">🔒 {name}</text>')
    else:
        out.append(f'<text x="24" y="38" font-size="17" font-weight="600" fill="{t["text"]}">{name}</text>')
    word = STATUS_WORD[item["status"]]
    title = ("🔒 " if item.get("wraps") else "") + fit(item["name"], 40)
    pill_x = 24 + text_width(title, 17, bold=True) + (8 if item.get("wraps") else 0) + 12
    pill_w = 26 + text_width(word, 10, bold=True) + len(word) * 0.6
    out += [
        f'<rect x="{pill_x:.0f}" y="24" width="{pill_w:.0f}" height="19" rx="9.5" fill="none" stroke="{color}"/>',
        f'<circle cx="{pill_x + 10:.0f}" cy="33.5" r="3.5" fill="{color}"/>',
        f'<circle class="pulse" cx="{pill_x + 10:.0f}" cy="33.5" r="3.5" fill="{color}"/>' if pulse else "",
        f'<text x="{pill_x + 18:.0f}" y="37.5" font-size="10" font-weight="600" letter-spacing=".6" fill="{color}">{word}</text>',
        f'<text x="24" y="60" font-size="13" fill="{t["muted"]}">{blurb}</text>',
        f'<text x="24" y="83" font-size="12" font-family="{MONO}" fill="{t["muted"]}">{latest}</text>',
    ]
    if language:
        dot = LANGUAGE_COLORS.get(language, t["muted"])
        out += [
            f'<text x="{W - 24}" y="30" font-size="12" text-anchor="end" fill="{t["muted"]}">{escape(language)}</text>',
            f'<circle cx="{W - 33 - text_width(language, 12):.0f}" cy="26" r="5" fill="{dot}"/>',
        ]
    out += [
        bars(item["buckets"], t, chart_x, 40),
        f'<text x="{W - 24}" y="90" font-size="11" text-anchor="end" fill="{t["muted"]}">'
        f'<tspan font-weight="600" fill="{t["text"]}">{item["count"]}</tspan> commit{"s" if item["count"] != 1 else ""} · {escape(item["span"])}</text>',
        "</g></svg>\n",
    ]
    return "".join(part for part in out if part)
