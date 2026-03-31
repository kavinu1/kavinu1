#!/usr/bin/env python3
"""
generate_streak_svg.py
Fetches GitHub contribution data via GraphQL API and generates a
streak stats SVG card matching the target design:
  - Total Contributions  |  Current Streak (ring)  |  Longest Streak
  - Dark background, orange accent, white/grey text
"""

import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN  = os.environ["GITHUB_TOKEN"]
USERNAME      = os.environ.get("GH_USERNAME",   "kavinu1")
OUTPUT_DARK   = os.environ.get("OUTPUT_DARK",   "generated/streak-stats-dark.svg")
OUTPUT_LIGHT  = os.environ.get("OUTPUT_LIGHT",  "generated/streak-stats-light.svg")

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# ── GraphQL – fetch all contribution weeks for the past year ─────────────────
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    createdAt
  }
}
"""

def graphql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type":  "application/json",
            "User-Agent":    "generate-streak-svg/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def fetch_contributions():
    today    = date.today()
    one_year_ago = today - timedelta(days=365)
    frm = one_year_ago.strftime("%Y-%m-%dT00:00:00Z")
    to  = today.strftime("%Y-%m-%dT23:59:59Z")

    data = graphql(QUERY, {"login": USERNAME, "from": frm, "to": to})
    user = data["data"]["user"]
    cal  = user["contributionsCollection"]["contributionCalendar"]
    created_at = user["createdAt"][:10]   # YYYY-MM-DD

    # Flatten all days in chronological order
    days = []
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort(key=lambda x: x[0])

    total = cal["totalContributions"]

    # ── Streaks ───────────────────────────────────────────────────────────────
    # Current streak: consecutive days with contributions ending today (or yesterday)
    today_str = today.strftime("%Y-%m-%d")
    yest_str  = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Build a set of days with contributions
    contrib_days = {d for d, c in days if c > 0}

    def calc_streak(end_date_str):
        """Count backwards from end_date_str."""
        d = date.fromisoformat(end_date_str)
        streak = 0
        streak_start = d
        while d.strftime("%Y-%m-%d") in contrib_days:
            streak += 1
            streak_start = d
            d -= timedelta(days=1)
        return streak, streak_start.strftime("%Y-%m-%d"), end_date_str

    # Current streak (count back from today; if today has no contribution yet, try yesterday)
    cur_streak, cur_start, cur_end = calc_streak(today_str)
    if cur_streak == 0:
        cur_streak, cur_start, cur_end = calc_streak(yest_str)

    # Longest streak: sliding window
    best, best_start, best_end = 0, days[0][0], days[0][0]
    run, run_start = 0, days[0][0]
    prev_date = None
    for d_str, c in days:
        d = date.fromisoformat(d_str)
        if c > 0:
            if prev_date and (d - prev_date).days == 1:
                run += 1
            else:
                run = 1
                run_start = d_str
            if run > best:
                best = run
                best_start = run_start
                best_end = d_str
        else:
            run = 0
        prev_date = d if c > 0 else prev_date

    # Account start date
    acct_start = created_at

    return {
        "total":       total,
        "acct_start":  acct_start,
        "cur_streak":  cur_streak,
        "cur_start":   cur_start if cur_streak else today_str,
        "cur_end":     cur_end   if cur_streak else today_str,
        "long_streak": best,
        "long_start":  best_start,
        "long_end":    best_end,
    }

# ── Date formatting ───────────────────────────────────────────────────────────
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

def fmt_date(d_str):
    """'2025-03-28' → 'Mar 28, 2025'"""
    d = date.fromisoformat(d_str)
    return f"{MONTHS[d.month-1]} {d.day}, {d.year}"

def fmt_range(start, end):
    """'2025-03-28' '2025-03-29' → 'Mar 28 - Mar 29'"""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    return f"{MONTHS[s.month-1]} {s.day} - {MONTHS[e.month-1]} {e.day}"

# ── SVG generation ────────────────────────────────────────────────────────────
def make_svg(s, dark=True):
    bg     = "#0d1117" if dark else "#fffefe"
    border = "#30363d" if dark else "#e4e2e2"
    divider = "#2d2d2d" if dark else "#e0dede"
    big_num = "#ffffff"  if dark else "#1c1c1c"
    label   = "#e0e0e0"  if dark else "#3d3d3d"
    sub     = "#8a8a8a"  if dark else "#767676"
    accent  = "none"

    W, H    = 480, 110
    SEC_W   = W // 3          # ~160 each section
    CX      = W // 2          # centre x for ring
    CY      = H // 2 + 2
    R       = 36
    circumference = 2 * math.pi * R

    # Ring fills based on whether there's a current streak
    streak_pct = min(s["cur_streak"] / max(s.get("long_streak", 1), 1), 1.0)
    dash_on    = circumference * streak_pct
    dash_off   = circumference - dash_on

    # Flame icon (simplified path, centred above ring)
    flame_d = ("M8.5 0c0 2.5-2 4-2 6.5a2.5 2.5 0 005 0C11.5 4 9.5 2.5 9.5 0zM5 "
               "9.5C3.343 9.5 2 10.843 2 12.5S3.343 15.5 5 15.5c1.657 0 3-1.343 "
               "3-3S6.657 9.5 5 9.5z")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
  <!-- Card -->
  <rect width="{W}" height="{H}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>

  <!-- Dividers -->
  <line x1="{SEC_W}" y1="15" x2="{SEC_W}" y2="{H-15}" stroke="{divider}" stroke-width="1"/>
  <line x1="{SEC_W*2}" y1="15" x2="{SEC_W*2}" y2="{H-15}" stroke="{divider}" stroke-width="1"/>

  <!-- ── LEFT: Total Contributions ── -->
  <text x="{SEC_W//2}" y="36" text-anchor="middle" font-size="26" font-weight="700"
        fill="{big_num}" font-family="{FONT}">{s['total']:,}</text>
  <text x="{SEC_W//2}" y="58" text-anchor="middle" font-size="12" font-weight="600"
        fill="{label}" font-family="{FONT}">Total Contributions</text>
  <text x="{SEC_W//2}" y="74" text-anchor="middle" font-size="10.5" fill="{sub}"
        font-family="{FONT}">{fmt_date(s['acct_start'])}</text>
  <text x="{SEC_W//2}" y="87" text-anchor="middle" font-size="10.5" fill="{sub}"
        font-family="{FONT}">- Present</text>

  <!-- ── MIDDLE: Current Streak (ring) ── -->
  <!-- Track ring -->
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" stroke="{divider}" stroke-width="4"/>
  <!-- Progress ring -->
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none"
          stroke="{accent}" stroke-width="4"
          stroke-dasharray="{dash_on:.2f} {dash_off:.2f}"
          stroke-linecap="round"
          transform="rotate(-90 {CX} {CY})"/>
  <!-- Small flame dot at top of ring -->
  <circle cx="{CX}" cy="{CY - R}" r="5" fill="{accent}"/>
  <!-- Streak number -->
  <text x="{CX}" y="{CY + 8}" text-anchor="middle" font-size="22" font-weight="700"
        fill="{accent}" font-family="{FONT}">{s['cur_streak']}</text>
  <!-- Label below ring -->
  <text x="{CX}" y="{H - 22}" text-anchor="middle" font-size="11.5" font-weight="600"
        fill="{accent}" font-family="{FONT}">Current Streak</text>
  <text x="{CX}" y="{H - 9}" text-anchor="middle" font-size="10" fill="{sub}"
        font-family="{FONT}">{fmt_range(s['cur_start'], s['cur_end'])}</text>

  <!-- ── RIGHT: Longest Streak ── -->
  <text x="{SEC_W*2 + SEC_W//2}" y="36" text-anchor="middle" font-size="26" font-weight="700"
        fill="{big_num}" font-family="{FONT}">{s['long_streak']}</text>
  <text x="{SEC_W*2 + SEC_W//2}" y="58" text-anchor="middle" font-size="12" font-weight="600"
        fill="{label}" font-family="{FONT}">Longest Streak</text>
  <text x="{SEC_W*2 + SEC_W//2}" y="74" text-anchor="middle" font-size="10.5" fill="{sub}"
        font-family="{FONT}">{fmt_range(s['long_start'], s['long_end'])}</text>
</svg>
"""
    return svg

def main():
    print(f"Fetching streak data for {USERNAME}...")
    try:
        stats = fetch_contributions()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP error: {e.code} {e.reason}\n{body}")
        sys.exit(1)

    print(f"  Total contributions: {stats['total']}")
    print(f"  Current streak:      {stats['cur_streak']} day(s)")
    print(f"  Longest streak:      {stats['long_streak']} day(s)")

    os.makedirs(os.path.dirname(OUTPUT_DARK)  or ".", exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_LIGHT) or ".", exist_ok=True)

    with open(OUTPUT_DARK, "w", encoding="utf-8") as f:
        f.write(make_svg(stats, dark=True))
    print(f"Written: {OUTPUT_DARK}")

    with open(OUTPUT_LIGHT, "w", encoding="utf-8") as f:
        f.write(make_svg(stats, dark=False))
    print(f"Written: {OUTPUT_LIGHT}")

if __name__ == "__main__":
    main()
