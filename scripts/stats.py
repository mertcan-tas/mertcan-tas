import json
import os
import urllib.request
from html import escape
from pathlib import Path

USER = "mertcan-tas"
IGNORED_LANGUAGES = {"HTML", "CSS", "SCSS"}
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "stats.svg"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        user = json.load(response)["data"]["user"]

    languages = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in IGNORED_LANGUAGES:
                continue
            entry = languages.setdefault(name, [0, edge["node"]["color"] or "#8b949e"])
            entry[0] += edge["size"]
    top = sorted(languages.items(), key=lambda item: item[1][0], reverse=True)[:4]
    total = sum(size for _, (size, _) in top) or 1
    contributions = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return contributions, [(name, color, size / total) for name, (size, color) in top]


def render(contributions, languages):
    width, height = 1200, 120
    bar_x, bar_y, bar_w = 420, 46, 732
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{contributions:,} contributions this year">',
        "<style>text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}.m{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}</style>",
        f'<rect width="{width}" height="{height}" fill="#000"/>',
        f'<rect width="6" height="{height}" fill="#276ef1"/>',
        f'<text x="48" y="70" font-size="44" font-weight="700" fill="#fafafa" letter-spacing="-1.5">{contributions:,}</text>',
        '<text x="48" y="96" class="m" font-size="15" fill="#7aa7ff">contributions this year</text>',
        f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>',
        '<g clip-path="url(#bar)">',
    ]
    offset = bar_x
    for _, color, share in languages:
        segment = bar_w * share
        parts.append(f'<rect x="{offset:.1f}" y="{bar_y}" width="{segment + 0.5:.1f}" height="8" fill="{color}"/>')
        offset += segment
    parts.append("</g>")

    slot = bar_w / max(len(languages), 1)
    for index, (name, color, share) in enumerate(languages):
        x = bar_x + index * slot
        parts.append(f'<circle cx="{x + 5:.1f}" cy="85" r="5" fill="{color}"/>')
        parts.append(f'<text x="{x + 16:.1f}" y="90" font-size="16" fill="#a1a1aa">{escape(name)} {share * 100:.0f}%</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(render(*fetch()), encoding="utf-8")


if __name__ == "__main__":
    main()
