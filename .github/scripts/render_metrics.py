#!/usr/bin/env python3
"""Generate the public GitHub metrics panel used by the profile README."""

from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


USERNAME = "AL-akhali"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DARK = ROOT / "assets" / "live-public-signal.svg"
OUTPUT_LIGHT = ROOT / "assets" / "live-public-signal-light.svg"
API = "https://api.github.com"


def github_json(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-metrics",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect():
    user = github_json(f"/users/{USERNAME}")
    repos = github_json(f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated")
    owned = [repo for repo in repos if not repo.get("fork")]
    languages = Counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(github_json, f"/repos/{USERNAME}/{repo['name']}/languages"): repo["name"]
            for repo in owned
        }
        for future in as_completed(futures):
            try:
                languages.update(future.result())
            except Exception as error:
                print(f"warning: skipped languages for {futures[future]}: {error}")
    return {
        "repos": int(user.get("public_repos", len(owned))),
        "followers": int(user.get("followers", 0)),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in owned),
        "forks": sum(int(repo.get("forks_count", 0)) for repo in owned),
        "languages": languages,
    }


def render(data, theme="dark"):
    if theme == "light":
        bg, panel, grid, fine = "#f5f1ea", "#fffdf9", "#d8cec2", "#e9e1d8"
        ink, white, muted = "#263a4d", "#172330", "#5f6870"
        brown, amber, cyan = "#b89a7e", "#9a6540", "#48657d"
    else:
        bg, panel, grid, fine = "#171717", "#20201f", "#34312d", "#24221f"
        ink, white, muted = "#dededa", "#f3f1eb", "#aaa69e"
        brown, amber, cyan = "#7a6048", "#a98262", "#c9b9a8"
    metrics = [
        ("PUBLIC REPOS", data["repos"]),
        ("TOTAL STARS", data["stars"]),
        ("TOTAL FORKS", data["forks"]),
        ("FOLLOWERS", data["followers"]),
    ]
    total = sum(data["languages"].values()) or 1
    top = data["languages"].most_common(5)
    rows = []
    for index, (name, amount) in enumerate(top):
        y = 326 + index * 31
        ratio = amount / total
        width = max(4, round(550 * ratio))
        rows.append(
            f'<text x="405" y="{y}" class="label">{escape(name.upper())}</text>'
            f'<rect class="track" x="595" y="{y-12}" width="550" height="10" rx="5" fill="{grid}"/>'
            f'<rect class="bar" x="595" y="{y-12}" width="{min(width, 550)}" height="10" rx="5" fill="{amber}"/>'
            f'<text x="1138" y="{y}" text-anchor="end" class="small">{ratio*100:.1f}%</text>'
        )
    cards = []
    for index, (label, value) in enumerate(metrics):
        x = 56 + index * 272
        cards.append(
            f'<rect class="card" x="{x}" y="157" width="244" height="105" rx="8" fill="{panel}" stroke="{brown}"/>'
            f'<path class="corner" d="M{x} {177}V157H{x+20} M{x+224} 157H{x+244}V177" stroke="{ink}" stroke-width="2"/>'
            f'<text x="{x+20}" y="191" class="metric">{value}</text>'
            f'<text x="{x+20}" y="232" class="label">{label}</text>'
        )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="520" viewBox="0 0 1200 520" role="img" aria-labelledby="title desc">
<title id="title">Live public GitHub signal for Anas Al-Akhali</title>
<desc id="desc">Automatically updated public repositories, stars, forks, followers and language distribution.</desc>
<style>
text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
.title {{ fill:{white};font:bold 31px Arial,sans-serif }} .sub {{ fill:{muted};font:15px Arial,sans-serif }}
.chrome {{ fill:{muted};font:bold 13px monospace }} .metric {{ fill:{white};font:bold 30px monospace }}
.label {{ fill:{cyan};font:bold 12px monospace }} .small {{ fill:{muted};font:11px monospace }}
</style>
<rect class="bg" width="1200" height="520" fill="{bg}"/>
<defs><pattern id="g" width="30" height="30" patternUnits="userSpaceOnUse"><path class="grid" d="M30 0H0V30" fill="none" stroke="{fine}"/></pattern></defs>
<rect width="1200" height="520" fill="url(#g)"/>
<circle cx="38" cy="32" r="5" fill="#ff6b6b"/><circle cx="62" cy="32" r="5" fill="{amber}"/><circle cx="86" cy="32" r="5" fill="{ink}"/>
<text x="112" y="36" class="chrome">SIGNAL://LIVE_PUBLIC_DATA</text><text x="1164" y="36" text-anchor="end" class="small">AUTO-SYNC / GITHUB API</text>
<path class="rule" d="M30 52H1170" stroke="{grid}"/>
<text x="56" y="104" class="title">LIVE PUBLIC SIGNAL</text>
<text x="56" y="137" class="sub">Verified public data. Generated from the official GitHub API.</text>
{''.join(cards)}
<text x="56" y="322" class="label">LANGUAGE STACK / PUBLIC CODE</text>
<path class="rule" d="M56 343H355 M355 300V465 M56 465H1144" stroke="{grid}"/>
<text x="56" y="382" class="metric">{len(top):02d}</text><text x="56" y="412" class="label">ACTIVE LANGUAGES</text>
<text x="56" y="448" class="small">SOURCE  api.github.com</text>
{''.join(rows)}
<text x="1144" y="495" text-anchor="end" class="small">LAST SYNC  {now}</text>
</svg>'''


if __name__ == "__main__":
    OUTPUT_DARK.parent.mkdir(parents=True, exist_ok=True)
    data = collect()
    OUTPUT_DARK.write_text(render(data, "dark"), encoding="utf-8")
    OUTPUT_LIGHT.write_text(render(data, "light"), encoding="utf-8")
    print(f"updated {OUTPUT_DARK} and {OUTPUT_LIGHT}")
