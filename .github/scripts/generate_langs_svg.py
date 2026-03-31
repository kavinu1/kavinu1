#!/usr/bin/env python3
"""
generate_langs_svg.py
Fetches language data from GitHub GraphQL API and generates a
dark-themed SVG that matches the "Most Used Languages" card design.
"""

import json
import os
import sys
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME     = os.environ.get("GH_USERNAME", "kavinu1")
OUTPUT_DARK  = os.environ.get("OUTPUT_DARK",  "generated/top-langs-dark.svg")
OUTPUT_LIGHT = os.environ.get("OUTPUT_LIGHT", "generated/top-langs-light.svg")
MAX_LANGS    = int(os.environ.get("MAX_LANGS", "6"))

# GitHub language colours (subset – extend as needed)
LANG_COLORS = {
    "JavaScript":  "#f1e05a",
    "TypeScript":  "#3178c6",
    "Python":      "#3572A5",
    "HTML":        "#e34c26",
    "CSS":         "#563d7c",
    "SCSS":        "#c6538c",
    "Shell":       "#89e051",
    "Ruby":        "#701516",
    "Go":          "#00ADD8",
    "Rust":        "#dea584",
    "Java":        "#b07219",
    "C":           "#555555",
    "C++":         "#f34b7d",
    "C#":          "#178600",
    "PHP":         "#4F5D95",
    "Swift":       "#F05138",
    "Kotlin":      "#A97BFF",
    "Dart":        "#00B4AB",
    "Vue":         "#41b883",
    "Svelte":      "#ff3e00",
    "Lua":         "#000080",
    "R":           "#198CE7",
    "Jupyter Notebook": "#DA5B0B",
    "MDX":         "#fcb32c",
    "Markdown":    "#083fa1",
}

FALLBACK_COLORS = [
    "#6e7681","#58a6ff","#bc8cff","#f78166","#56d364",
    "#e3b341","#db6d28","#ffa657","#79c0ff","#d2a8ff",
]

# ── GraphQL query ────────────────────────────────────────────────────────────
QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
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
            "User-Agent":    "generate-langs-svg/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def fetch_language_sizes():
    data = graphql(QUERY, {"login": USERNAME})
    sizes = {}
    colors_from_api = {}
    for repo in data["data"]["user"]["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name  = edge["node"]["name"]
            color = edge["node"]["color"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            if color and name not in colors_from_api:
                colors_from_api[name] = color
    return sizes, colors_from_api

def top_langs(sizes, colors_from_api):
    total = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:MAX_LANGS]
    result = []
    for i, (name, size) in enumerate(ranked):
        pct   = size / total * 100
        color = (
            LANG_COLORS.get(name)
            or colors_from_api.get(name)
            or FALLBACK_COLORS[i % len(FALLBACK_COLORS)]
        )
        result.append({"name": name, "pct": pct, "color": color})
    return result

# ── SVG generation ──────────────────────────────────────────────────────────
def make_svg(langs, dark=True):
    bg      = "#0d1117" if dark else "#ffffff"
    title   = "#e6edf3" if dark else "#24292f"
    label   = "#e6edf3" if dark else "#24292f"
    pct_clr = "#8b949e" if dark else "#57606a"
    track   = "#21262d" if dark else "#eaedf0"
    border  = "#30363d" if dark else "#d0d7de"

    BAR_W   = 260   # max bar width (px)
    BAR_H   = 8
    ROW_H   = 36
    PAD_X   = 20
    PAD_TOP = 50

    height = PAD_TOP + len(langs) * ROW_H + 20
    width  = 400

    rows = []
    for i, lang in enumerate(langs):
        y      = PAD_TOP + i * ROW_H
        bar_px = max(2, BAR_W * lang["pct"] / 100)
        pct_s  = f"{lang['pct']:.2f}%"

        rows.append(f"""
  <!-- {lang['name']} -->
  <text x="{PAD_X}" y="{y + 13}" font-size="13" fill="{lang['color']}" font-weight="600"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">{lang['name']}</text>
  <text x="{width - PAD_X}" y="{y + 13}" font-size="12" fill="{pct_clr}" text-anchor="end"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">{pct_s}</text>
  <rect x="{PAD_X}" y="{y + 20}" width="{BAR_W}" height="{BAR_H}" rx="4" fill="{track}"/>
  <rect x="{PAD_X}" y="{y + 20}" width="{bar_px:.2f}" height="{BAR_H}" rx="4" fill="{lang['color']}"/>""")

    rows_svg = "".join(rows)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" rx="10" fill="{bg}" stroke="{border}" stroke-width="1"/>
  <text x="{PAD_X}" y="30" font-size="16" font-weight="700" fill="{title}"
        font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">Most Used Languages</text>
{rows_svg}
</svg>
"""

def main():
    print(f"Fetching language data for {USERNAME}...")
    try:
        sizes, colors_from_api = fetch_language_sizes()
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} {e.reason}")
        sys.exit(1)

    langs = top_langs(sizes, colors_from_api)
    if not langs:
        print("No language data found.")
        sys.exit(1)

    print("Top languages:")
    for l in langs:
        print(f"  {l['name']:20s} {l['pct']:6.2f}%  {l['color']}")

    os.makedirs(os.path.dirname(OUTPUT_DARK)  or ".", exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_LIGHT) or ".", exist_ok=True)

    with open(OUTPUT_DARK, "w", encoding="utf-8") as f:
        f.write(make_svg(langs, dark=True))
    print(f"Written: {OUTPUT_DARK}")

    with open(OUTPUT_LIGHT, "w", encoding="utf-8") as f:
        f.write(make_svg(langs, dark=False))
    print(f"Written: {OUTPUT_LIGHT}")

if __name__ == "__main__":
    main()
