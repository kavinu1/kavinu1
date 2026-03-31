#!/usr/bin/env python3
"""
generate_stats_svg.py
Fetches GitHub user stats via the GraphQL API and generates a styled
SVG card matching the target design:
  - Dark/light card with rounded corners
  - Stats rows: Total Stars, Total Commits, Total PRs, Total Issues,
    Contributed to
  - Circular rank badge (A++, A+, A, B+, B, C) top-right
"""

import json
import math
import os
import sys
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN  = os.environ["GITHUB_TOKEN"]
USERNAME      = os.environ.get("GH_USERNAME",    "kavinu1")
OUTPUT_DARK   = os.environ.get("OUTPUT_DARK",    "generated/github-stats-dark.svg")
OUTPUT_LIGHT  = os.environ.get("OUTPUT_LIGHT",   "generated/github-stats-light.svg")

# ── GraphQL query ─────────────────────────────────────────────────────────────
QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        stargazerCount
        languages(first: 1) { nodes { name } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    pullRequests(states: MERGED) { totalCount }
    issues(states: OPEN)         { totalCount }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
      includeUserRepositories: false
      first: 1
    ) { totalCount }
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
            "User-Agent":    "generate-stats-svg/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def fetch_stats():
    data  = graphql(QUERY, {"login": USERNAME})
    user  = data["data"]["user"]
    cc    = user["contributionsCollection"]

    total_stars   = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    total_commits = (cc["totalCommitContributions"]
                     + cc["restrictedContributionsCount"])
    total_prs     = user["pullRequests"]["totalCount"]
    total_issues  = user["issues"]["totalCount"]
    contributed   = user["repositoriesContributedTo"]["totalCount"]
    display_name  = user["name"] or USERNAME

    return {
        "name":          display_name,
        "total_stars":   total_stars,
        "total_commits": total_commits,
        "total_prs":     total_prs,
        "total_issues":  total_issues,
        "contributed":   contributed,
    }

# ── Rank calculation ──────────────────────────────────────────────────────────
def calc_rank(stats):
    """Simple exponential-decay rank similar to github-readme-stats."""
    weights = {
        "commits":    2,
        "prs":        3,
        "issues":     1,
        "stars":      4,
        "contributed": 1,
    }
    values = {
        "commits":     stats["total_commits"],
        "prs":         stats["total_prs"],
        "issues":      stats["total_issues"],
        "stars":       stats["total_stars"],
        "contributed": stats["contributed"],
    }
    LEVELS = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    score  = 0
    total_w = sum(weights.values())
    for k, w in weights.items():
        # clamp percentile; higher is better
        v = min(values[k], 1000)
        pct = min(v / 100.0 * 100, 100)
        score += (w / total_w) * (100 - math.exp(-pct / 14.495) * 100)

    thresholds = [
        (90, "S",   "#e3a008"),
        (75, "A++", "#e3a008"),
        (60, "A+",  "#e3a008"),
        (45, "A",   "#e3a008"),
        (30, "B+",  "#58a6ff"),
        (20, "B",   "#58a6ff"),
        (10, "C",   "#8b949e"),
    ]
    for threshold, label, color in thresholds:
        if score >= threshold:
            return label, color, score
    return "C", "#8b949e", score

# ── SVG helpers ───────────────────────────────────────────────────────────────
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# SVG icons (16×16 path data from Octicons)
ICON_STAR   = "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.873 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"
ICON_COMMIT = "M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z"
ICON_PR     = "M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"
ICON_ISSUE  = "M8 9.5a1.5 1.5 0 100-3 1.5 1.5 0 000 3z M8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z"
ICON_CONTRIB= "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z"

def fmt(n):
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

def make_svg(stats, rank_label, rank_color, dark=True):
    bg     = "#0d1117" if dark else "#fffefe"
    border = "#30363d" if dark else "#e4e2e2"
    title  = "#e6edf3" if dark else "#2d333b"
    text   = "#c9d1d9" if dark else "#434d58"
    icon   = "#f0883e"   # orange — same in both themes
    subtext= "#8b949e" if dark else "#767676"

    W, H   = 495, 165
    PAD    = 25
    name   = stats["name"]

    # Rank badge geometry
    CX, CY, R = 420, 85, 38
    TRACK_C    = "#30363d" if dark else "#dce1e6"
    BADGE_BG   = "#0d1117" if dark else "#fffefe"

    # Circumference for the progress ring
    circumference = 2 * math.pi * (R - 5)
    # Map score (0-100) → dasharray offset so ring fills proportionally
    score_pct = min(float(os.environ.get("_RANK_SCORE", "50")), 100)
    dash_filled = circumference * score_pct / 100
    dash_empty  = circumference - dash_filled

    rows = [
        ("⭐", ICON_STAR,    "Total Stars:",     fmt(stats["total_stars"])),
        ("🔄", ICON_COMMIT,  "Total Commits:",   fmt(stats["total_commits"])),
        ("📌", ICON_PR,      "Total PRs:",       fmt(stats["total_prs"])),
        ("🐛", ICON_ISSUE,   "Total Issues:",    fmt(stats["total_issues"])),
        ("📚", ICON_CONTRIB, "Contributed to:",  fmt(stats["contributed"])),
    ]

    ROW_H  = 22
    START_Y = 60
    rows_svg = []
    for i, (_, icon_path, label, value) in enumerate(rows):
        y = START_Y + i * ROW_H
        rows_svg.append(f"""
  <svg x="{PAD}" y="{y - 12}" width="16" height="16" viewBox="0 0 16 16" fill="{icon}">
    <path fill-rule="evenodd" d="{icon_path}"/>
  </svg>
  <text x="{PAD + 22}" y="{y}" font-size="13.5" fill="{text}" font-family="{FONT}">{label}</text>
  <text x="{PAD + 180}" y="{y}" font-size="13.5" fill="{title}" font-weight="700"
        font-family="{FONT}">{value}</text>""")

    rows_joined = "".join(rows_svg)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">
  <!-- Card background -->
  <rect width="{W}" height="{H}" rx="10" fill="{bg}" stroke="{border}" stroke-width="1"/>

  <!-- Title -->
  <text x="{PAD}" y="38" font-size="17" font-weight="700" fill="{title}"
        font-family="{FONT}">{name}'s GitHub Stats</text>

  <!-- Stats rows -->
{rows_joined}

  <!-- Rank badge track -->
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="{BADGE_BG}" stroke="{TRACK_C}" stroke-width="6"/>
  <!-- Rank badge ring -->
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none"
          stroke="{rank_color}" stroke-width="6"
          stroke-dasharray="{dash_filled:.2f} {dash_empty:.2f}"
          stroke-linecap="round"
          transform="rotate(-90 {CX} {CY})"/>
  <!-- Rank label -->
  <text x="{CX}" y="{CY + 6}" font-size="18" font-weight="700" fill="{rank_color}"
        text-anchor="middle" font-family="{FONT}">{rank_label}</text>
</svg>
"""
    return svg

def main():
    print(f"Fetching stats for {USERNAME}...")
    try:
        stats = fetch_stats()
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} {e.reason}")
        sys.exit(1)

    print(f"  Stars:     {stats['total_stars']}")
    print(f"  Commits:   {stats['total_commits']}")
    print(f"  PRs:       {stats['total_prs']}")
    print(f"  Issues:    {stats['total_issues']}")
    print(f"  Contrib:   {stats['contributed']}")

    rank_label, rank_color, score = calc_rank(stats)
    print(f"  Rank:      {rank_label}  (score={score:.1f})")

    # Pass score to SVG builder via env
    os.environ["_RANK_SCORE"] = str(score)

    os.makedirs(os.path.dirname(OUTPUT_DARK)  or ".", exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_LIGHT) or ".", exist_ok=True)

    with open(OUTPUT_DARK, "w", encoding="utf-8") as f:
        f.write(make_svg(stats, rank_label, rank_color, dark=True))
    print(f"Written: {OUTPUT_DARK}")

    with open(OUTPUT_LIGHT, "w", encoding="utf-8") as f:
        f.write(make_svg(stats, rank_label, rank_color, dark=False))
    print(f"Written: {OUTPUT_LIGHT}")

if __name__ == "__main__":
    main()
