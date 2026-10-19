#!/usr/bin/env python3
"""Refresh public GitHub profile data and self-hosted SVG cards.

The script uses GitHub Actions' GITHUB_TOKEN when available, edits only the
README section between AUTO_PROFILE markers, and writes local SVG assets. It
never fabricates contribution counts: if GraphQL activity retrieval fails, the
previous graph is preserved (or a clear first-run placeholder is written).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape as xml_escape

USERNAME = os.environ.get("PROFILE_USERNAME", "yatharth2soni")
README_PATH = Path(os.environ.get("README_PATH", "README.md"))
ASSET_DIR = Path(os.environ.get("ASSET_DIR", "assets"))
API_ROOT = "https://api.github.com"
MAX_REPOS = 12
MAX_PRS = 8
TIMEOUT_SECONDS = 30
# The owner asked to keep these coding-platform repositories out of the profile README.
HIDDEN_REPO_TERMS = ("leetcode", "codeforces")

from profile_intro import generate_intro_gif


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "yatharth2soni-profile-readme-sync",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:500]
        # GITHUB_TOKEN is scoped to the profile repository. If it cannot read a
        # public repository outside that scope, retry the GET anonymously.
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token and method == "GET" and exc.code in (403, 404):
            anonymous_headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "yatharth2soni-profile-readme-sync",
            }
            retry = Request(url, headers=anonymous_headers, method="GET")
            try:
                with urlopen(retry, timeout=TIMEOUT_SECONDS) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:
                pass
        raise RuntimeError(f"GitHub API HTTP {exc.code} for {url}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach GitHub API for {url}: {exc}") from exc


def api_get(path: str, params: dict | None = None) -> dict | list:
    url = f"{API_ROOT}{path}"
    if params:
        url += "?" + urlencode(params)
    return request_json(url)


def search_total(query: str) -> int:
    data = api_get("/search/issues", {"q": query, "per_page": 1})
    return int(data.get("total_count", 0))


def clean_cell(value: object, limit: int = 100) -> str:
    text = str(value or "").replace("|", r"\|").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text or "—"


def date_only(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return "—"


def owner_repo_from_item(item: dict) -> str:
    repository_api_url = item.get("repository_url", "")
    match = re.search(r"https://api\.github\.com/repos/([^/]+/[^/]+)$", repository_api_url)
    return match.group(1) if match else ""


def pr_state(item: dict) -> str:
    """Resolve OPEN/MERGED/CLOSED accurately, not just search-result state."""
    owner_repo = owner_repo_from_item(item)
    number = item.get("number")
    if owner_repo and number:
        try:
            details = api_get(f"/repos/{owner_repo}/pulls/{number}")
            if details.get("merged_at"):
                return "MERGED"
            return "OPEN" if details.get("state") == "open" else "CLOSED"
        except RuntimeError as exc:
            print(f"Warning: couldn't fetch PR status for {owner_repo}#{number}: {exc}", file=sys.stderr)
    if item.get("state") == "open":
        return "OPEN"
    # Without the detail endpoint, do not falsely label a closed PR as merged.
    return "CLOSED"


def should_hide_name(name: str | None) -> bool:
    value = (name or "").lower()
    return value == USERNAME.lower() or value.endswith("/" + USERNAME.lower()) or any(term in value for term in HIDDEN_REPO_TERMS)


def visible_public_repositories(repos: list[dict]) -> list[dict]:
    return [
        repo for repo in repos
        if not repo.get("private", False)
        and not should_hide_name(repo.get("name"))
        and not should_hide_name(repo.get("full_name"))
    ]


def normalize_pull_requests(items: list[dict]) -> list[dict]:
    """Prepare public PR entries once so README table and animation show same statuses."""
    result: list[dict] = []
    for item in items:
        owner_repo = owner_repo_from_item(item)
        title = item.get("title") or "Untitled pull request"
        if not owner_repo or should_hide_name(owner_repo) or should_hide_name(title):
            continue
        number = item.get("number")
        if not number:
            continue
        result.append({
            "repo": owner_repo.split("/")[-1],
            "full_repo": owner_repo,
            "number": int(number),
            "title": title,
            "url": item.get("html_url", f"https://github.com/{owner_repo}/pull/{number}"),
            "status": pr_state(item),
            "updated": date_only(item.get("updated_at")),
        })
        if len(result) >= MAX_PRS:
            break
    return result


def build_dynamic_section(repos: list[dict], open_count: int, merged_count: int, pull_requests: list[dict]) -> str:
    public_repos = sorted(
        visible_public_repositories(repos),
        key=lambda repo: repo.get("pushed_at") or repo.get("updated_at") or "",
        reverse=True,
    )
    stars = sum(int(repo.get("stargazers_count") or 0) for repo in public_repos)
    parts: list[str] = [
        '<div align="center">',
        f"**PUBLIC REPOSITORIES: {len(public_repos)}**　 **STARS: {stars}**　 **OPEN PRs: {open_count}**　 **MERGED PRs: {merged_count}**",
        "</div>",
        "",
        "#### `./repositories` — recently pushed public repositories",
        "",
        "| REPOSITORY | DESCRIPTION | LANGUAGE | ⭐ | LAST PUSH |",
        "|:--|:--|:--|--:|:--|",
    ]
    for repo in public_repos[:MAX_REPOS]:
        repo_name = clean_cell(repo.get("name"), 50)
        url = repo.get("html_url", f"https://github.com/{USERNAME}/{repo.get('name', '')}")
        description = clean_cell(repo.get("description") or "No description added yet.", 80)
        language = clean_cell(repo.get("language") or "—", 22)
        stars_num = int(repo.get("stargazers_count") or 0)
        pushed = date_only(repo.get("pushed_at"))
        parts.append(f"| [{repo_name}]({url}) | {description} | {language} | {stars_num} | {pushed} |")
    if not public_repos:
        parts.append("| No public repositories found | — | — | 0 | — |")
    parts += ["", f"[View all public repositories →](https://github.com/{USERNAME}?tab=repositories)"]

    parts += ["", "#### `./pull-requests` — latest public pull-request activity", "", "| REPOSITORY | PULL REQUEST | STATUS | UPDATED |", "|:--|:--|:--:|:--|"]
    for item in pull_requests:
        repo_name = clean_cell(item["repo"], 45)
        title = clean_cell(item["title"], 86)
        pr_url = item["url"]
        status = item["status"]
        updated = item["updated"]
        parts.append(f"| [{repo_name}](https://github.com/{item['full_repo']}) | [{title}](<{pr_url}>) | **{status}** | {updated} |")
    if not pull_requests:
        parts.append("| No public pull requests found | — | — | — |")

    parts += ["", "<sub>Generated from GitHub's public API · refreshed by the hourly workflow.</sub>"]
    return "\n".join(parts)


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def svg_document(width: int, height: int, contents: str, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{xml_escape(title)}</title><desc id="desc">Profile graphic generated by GitHub Actions.</desc>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="7" fill="#000" stroke="#888"/>
{contents}
</svg>\n'''


def svg_text(x: float, y: float, value: object, size: int = 12, color: str = "#eee", weight: str = "400", anchor: str | None = None) -> str:
    anchor_attr = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{size}" font-weight="{weight}"{anchor_attr}>{xml_escape(str(value))}</text>'


def render_stats_svg(metrics: dict) -> str:
    width, height = 960, 150
    labels = [
        ("PUBLIC REPOSITORIES", str(metrics.get("repositories", "—"))),
        ("TOTAL STARS", str(metrics.get("stars", "—"))),
        ("OPEN PRs", str(metrics.get("open_prs", "—"))),
        ("MERGED PRs", str(metrics.get("merged_prs", "—"))),
    ]
    content = [svg_text(24, 27, "$ github --summary", 12, "#aaa")]
    gap = 10
    x0 = 20
    card_w = (width - 2*x0 - gap*(len(labels)-1)) / len(labels)
    for i, (label, value) in enumerate(labels):
        x = x0 + i*(card_w+gap)
        content.append(f'<rect x="{x:.1f}" y="42" width="{card_w:.1f}" height="82" rx="5" fill="#050505" stroke="#777"/>')
        content.append(svg_text(x+card_w/2, 75, value, 28, "#fff", "700", "middle"))
        content.append(svg_text(x+card_w/2, 101, label, 9, "#bbb", "400", "middle"))
    return svg_document(width, height, "\n".join(content), "GitHub public profile metrics")


def render_language_svg(language_bytes: Counter[str]) -> str:
    width, height = 960, 236
    content = [svg_text(24, 28, "$ github --language-bytes", 12, "#aaa"), svg_text(24, 48, "GitHub-reported language byte totals across owned public repositories (excluding forks)", 11, "#ccc")]
    top = language_bytes.most_common(5)
    if not top or sum(language_bytes.values()) == 0:
        content.append(svg_text(24, 104, "Language data will appear after the first successful Actions sync.", 13, "#ddd"))
        return svg_document(width, height, "\n".join(content), "Public repository language distribution")
    total = sum(language_bytes.values())
    bar_x, bar_width = 210, 590
    for i, (name, size) in enumerate(top):
        y = 78 + i*30
        pct = size / total * 100
        content.append(svg_text(24, y+10, name, 12, "#eee"))
        content.append(f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="10" rx="2" fill="#202020"/>')
        content.append(f'<rect x="{bar_x}" y="{y}" width="{max(1, bar_width*pct/100):.2f}" height="10" rx="2" fill="#eee"/>')
        content.append(svg_text(900, y+10, f"{pct:.1f}%", 11, "#ddd", anchor="end"))
    return svg_document(width, height, "\n".join(content), "GitHub language composition")


def render_pr_contribution_pie_svg(pull_requests: list[dict]) -> str:
    """Render a multicolour pie chart for recent public PRs grouped by repository.

    The chart is deliberately described as recent PR mix (not all historical
    contributions): `pull_requests` is the same bounded list used in the live
    README PR table, so its counts have a clear and verifiable scope.
    """
    width, height = 960, 292
    palette = [
        "#38BDF8",  # sky
        "#A78BFA",  # violet
        "#34D399",  # emerald
        "#F59E0B",  # amber
        "#FB7185",  # rose
        "#2DD4BF",  # teal
        "#818CF8",  # indigo
        "#F472B6",  # pink
    ]
    by_repo: Counter[str] = Counter()
    for item in pull_requests:
        repo = str(item.get("full_repo") or item.get("repo") or "").strip()
        if repo:
            by_repo[repo] += 1

    content = [
        svg_text(24, 28, "$ git --contribution-mix", 12, "#eee", "600"),
        svg_text(24, 48, f"Recent public PRs by repository · latest {MAX_PRS} tracked entries", 11, "#aaa"),
    ]
    if not by_repo:
        content.append(svg_text(24, 142, "Public pull-request data will appear after the first successful sync.", 13, "#bbb"))
        content.append(svg_text(24, 165, "This chart is generated from GitHub's public pull-request results; no sample counts are used.", 10, "#777"))
        return svg_document(width, height, "\n".join(content), "Recent public pull requests by repository")

    # Use a real SVG pie chart (not an external image) so GitHub can serve it
    # directly from the profile repository and Actions can refresh it hourly.
    cx, cy, radius = 166.0, 166.0, 82.0
    entries = by_repo.most_common()
    total = sum(by_repo.values())
    angle = -90.0
    for index, (repo, count) in enumerate(entries):
        sweep = 360.0 * count / total
        end_angle = angle + sweep
        x1 = cx + radius * math.cos(math.radians(angle))
        y1 = cy + radius * math.sin(math.radians(angle))
        x2 = cx + radius * math.cos(math.radians(end_angle))
        y2 = cy + radius * math.sin(math.radians(end_angle))
        large_arc = 1 if sweep > 180 else 0
        colour = palette[index % len(palette)]
        path = (
            f'<path d="M {cx:.2f} {cy:.2f} L {x1:.2f} {y1:.2f} '
            f'A {radius:.2f} {radius:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f} Z" '
            f'fill="{colour}" stroke="#fff" stroke-width="1.1"><title>{xml_escape(repo)}: {count} PR(s)</title></path>'
        )
        content.append(path)
        angle = end_angle

    legend_x = 302
    legend_y = 78
    legend_gap = 25
    content.append(svg_text(legend_x, 61, f"{total} TRACKED PUBLIC PRs", 10, "#eee", "600"))
    for index, (repo, count) in enumerate(entries):
        y = legend_y + index * legend_gap
        colour = palette[index % len(palette)]
        percentage = count / total * 100
        content.append(f'<rect x="{legend_x}" y="{y-10}" width="12" height="12" rx="2" fill="{colour}" stroke="#fff" stroke-width=".5"/>')
        content.append(svg_text(legend_x + 24, y, repo, 11, "#eee"))
        content.append(svg_text(925, y, f"{count}  ·  {percentage:.0f}%", 10, colour, "600", "end"))
    content.append(svg_text(legend_x, height - 12, "Colors identify repositories · list refreshed by GitHub Actions", 9, "#777"))
    return svg_document(width, height, "\n".join(content), "Recent public pull-request contribution mix by repository")


def render_contribution_svg(calendar: dict) -> str:
    width, height = 960, 178
    weeks = calendar.get("weeks") or []
    total = int(calendar.get("totalContributions") or 0)
    cell, gap = 10, 4
    step = cell + gap
    x0, y0 = 70, 54
    content = [
        svg_text(24, 27, "$ github --heatmap", 12, "#aaa"),
        svg_text(935, 27, f"{total:,} contributions · last year", 11, "#eee", anchor="end"),
    ]
    # Month labels and activity squares come directly from GraphQL's contribution calendar.
    previous_month = None
    shades = ["#151515", "#3e3e3e", "#696969", "#a0a0a0", "#fff"]
    for wi, week in enumerate(weeks):
        days = week.get("contributionDays") or []
        if not days:
            continue
        first_date = days[0].get("date", "")
        try:
            month = date.fromisoformat(first_date).month
            if month != previous_month:
                content.append(svg_text(x0 + wi*step, 45, date.fromisoformat(first_date).strftime("%b"), 9, "#aaa"))
                previous_month = month
        except ValueError:
            pass
        for di, day in enumerate(days):
            try:
                d = date.fromisoformat(day.get("date", ""))
            except ValueError:
                continue
            weekday = day.get("weekday")
            if weekday is None:
                weekday = (d.weekday() + 1) % 7  # GraphQL calendar uses Sunday=0.
            count = int(day.get("contributionCount") or 0)
            level = 0 if count == 0 else (1 if count <= 2 else (2 if count <= 4 else (3 if count <= 7 else 4)))
            x, y = x0 + wi*step, y0 + int(weekday)*step
            tooltip = f"{d.isoformat()}: {count} contribution(s)"
            content.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{shades[level]}" stroke="#333" stroke-width=".3"><title>{xml_escape(tooltip)}</title></rect>')
    for label, weekday in [("Mon",1),("Wed",3),("Fri",5)]:
        content.append(svg_text(24, y0 + weekday*step + 9, label, 9, "#aaa"))
    legend_y = 162
    content.append(svg_text(650, legend_y, "LESS", 9, "#aaa"))
    for i, shade in enumerate(shades):
        content.append(f'<rect x="682" y="{legend_y-9}" width="10" height="10" rx="2" fill="{shade}" stroke="#333" stroke-width=".3"/>')
    content.append(svg_text(762, legend_y, "MORE", 9, "#aaa"))
    content.append(svg_text(24, 162, "Public activity shown by GitHub", 9, "#777"))
    return svg_document(width, height, "\n".join(content), "GitHub contribution calendar")


def placeholder_contribution_svg() -> str:
    content = "\n".join([
        svg_text(24, 28, "$ github --heatmap", 12, "#aaa"),
        svg_text(24, 72, "Contribution chart will populate after the first successful GitHub Actions sync.", 14, "#eee"),
        svg_text(24, 99, "The workflow uses GitHub's contribution calendar; no sample or invented activity is shown.", 11, "#aaa"),
        svg_text(24, 139, "Repository → Actions → Sync GitHub profile README → Run workflow", 10, "#ddd"),
    ])
    return svg_document(960, 178, content, "GitHub contribution calendar awaiting first sync")


def placeholder_stats_svg() -> str:
    return render_stats_svg({"repositories": 10, "stars": 0, "open_prs": 2, "merged_prs": 3})


def generate_language_bytes(repos: list[dict]) -> Counter[str]:
    totals: Counter[str] = Counter()
    candidates = [r for r in visible_public_repositories(repos) if not r.get("fork", False) and not r.get("archived", False)]
    for repo in candidates[:50]:
        full_name = repo.get("full_name")
        if not full_name:
            continue
        try:
            data = api_get(f"/repos/{full_name}/languages")
            if isinstance(data, dict):
                for language, size in data.items():
                    totals[language] += int(size)
        except (RuntimeError, ValueError, TypeError) as exc:
            print(f"Warning: skipping language metadata for {full_name}: {exc}", file=sys.stderr)
    return totals


def fetch_contribution_calendar_from_graphql() -> dict:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    end = today + timedelta(days=1)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              firstDay
              contributionDays { date contributionCount weekday }
            }
          }
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T00:00:00Z",
        },
    }
    response = request_json("https://api.github.com/graphql", method="POST", payload=payload)
    if response.get("errors"):
        messages = "; ".join(err.get("message", "unknown GraphQL error") for err in response["errors"])
        raise RuntimeError(f"GraphQL contribution query failed: {messages}")
    user = (response.get("data") or {}).get("user") or {}
    calendar = ((user.get("contributionsCollection") or {}).get("contributionCalendar"))
    if not calendar or not isinstance(calendar.get("weeks"), list):
        raise RuntimeError("GitHub did not return a contribution calendar.")
    return calendar


def fetch_contribution_calendar_from_public_profile() -> dict:
    """Fallback: parse the public contribution-grid SVG embedded by GitHub itself."""
    url = f"https://github.com/users/{USERNAME}/contributions"
    request = Request(url, headers={"User-Agent": "yatharth2soni-profile-readme-sync", "Accept": "text/html"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            page = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Could not fetch GitHub public contribution page: {exc}") from exc

    day_counts: dict[date, int] = {}
    for tag in re.findall(r"<rect\b[^>]*>", page):
        date_match = re.search(r'data-date=[\"\'](\d{4}-\d{2}-\d{2})[\"\']', tag)
        count_match = re.search(r'data-count=[\"\'](\d+)[\"\']', tag)
        if not date_match:
            continue
        try:
            day = date.fromisoformat(date_match.group(1))
        except ValueError:
            continue
        if count_match:
            count = int(count_match.group(1))
        else:
            label = re.search(r'aria-label=[\"\']([^\"\']*)[\"\']', tag)
            if not label:
                continue
            found_count = re.search(r"(\d+) contribution", label.group(1), re.I)
            count = int(found_count.group(1)) if found_count else 0
        day_counts[day] = count
    if not day_counts:
        raise RuntimeError("Could not find daily contribution counts on GitHub's public profile page.")

    start_day, end_day = min(day_counts), max(day_counts)
    week_start = start_day - timedelta(days=(start_day.weekday() + 1) % 7)
    weeks = []
    total = 0
    while week_start <= end_day:
        days = []
        for weekday in range(7):
            d = week_start + timedelta(days=weekday)
            count = day_counts.get(d, 0)
            total += count
            days.append({"date": d.isoformat(), "contributionCount": count, "weekday": weekday})
        weeks.append({"firstDay": week_start.isoformat(), "contributionDays": days})
        week_start += timedelta(days=7)
    return {"totalContributions": total, "weeks": weeks}


def fetch_contribution_calendar() -> dict:
    try:
        return fetch_contribution_calendar_from_graphql()
    except (RuntimeError, ValueError, KeyError, TypeError) as graphql_error:
        print(f"GraphQL contribution retrieval failed; trying GitHub's public profile graph: {graphql_error}", file=sys.stderr)
        return fetch_contribution_calendar_from_public_profile()


def update_assets(repos: list[dict], open_count: int, merged_count: int, pull_requests: list[dict]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    public_repos = visible_public_repositories(repos)
    metrics = {
        "repositories": len(public_repos),
        "stars": sum(int(r.get("stargazers_count") or 0) for r in public_repos),
        "open_prs": open_count,
        "merged_prs": merged_count,
    }
    write_if_changed(ASSET_DIR / "github-stats.svg", render_stats_svg(metrics))
    languages = generate_language_bytes(public_repos)
    write_if_changed(ASSET_DIR / "language-stats.svg", render_language_svg(languages))
    write_if_changed(ASSET_DIR / "contribution-pie.svg", render_pr_contribution_pie_svg(pull_requests))
    generate_intro_gif(ASSET_DIR / "profile-intro.gif", open_count, merged_count, pull_requests)
    try:
        calendar = fetch_contribution_calendar()
        write_if_changed(ASSET_DIR / "contribution-graph.svg", render_contribution_svg(calendar))
        print(f"Contribution graph refreshed ({calendar.get('totalContributions', 0)} contributions in the queried calendar).")
    except (RuntimeError, ValueError, KeyError) as exc:
        graph_path = ASSET_DIR / "contribution-graph.svg"
        print(f"Warning: contribution graph not refreshed: {exc}", file=sys.stderr)
        if not graph_path.exists():
            write_if_changed(graph_path, placeholder_contribution_svg())


def main() -> int:
    if not README_PATH.exists():
        print(f"Unable to read {README_PATH}", file=sys.stderr)
        return 1
    readme = README_PATH.read_text(encoding="utf-8")
    start_marker = "<!-- AUTO_PROFILE_START -->"
    end_marker = "<!-- AUTO_PROFILE_END -->"
    if start_marker not in readme or end_marker not in readme:
        print("README is missing AUTO_PROFILE markers; no changes made.", file=sys.stderr)
        return 1
    start = readme.index(start_marker) + len(start_marker)
    end = readme.index(end_marker)
    if end <= start:
        print("README AUTO_PROFILE markers are out of order.", file=sys.stderr)
        return 1

    try:
        repos_response = api_get(f"/users/{USERNAME}/repos", {
            "type": "owner", "sort": "updated", "direction": "desc", "per_page": 100,
        })
        if not isinstance(repos_response, list):
            raise RuntimeError("Unexpected GitHub repositories response.")
        repos = [repo for repo in repos_response if not repo.get("private", False)]
        open_count = search_total(f"author:{USERNAME} type:pr is:open")
        merged_count = search_total(f"author:{USERNAME} type:pr is:merged")
        pr_response = api_get(
            "/search/issues",
            {"q": f"author:{USERNAME} type:pr", "sort": "updated", "order": "desc", "per_page": MAX_PRS * 3},
        )
        raw_pull_requests = pr_response.get("items", [])
        pull_requests = normalize_pull_requests(raw_pull_requests)
        generated = "\n\n" + build_dynamic_section(repos, open_count, merged_count, pull_requests).strip() + "\n\n"
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"Profile sync failed; preserving the current README section: {exc}", file=sys.stderr)
        return 1

    new_readme = readme[:start] + generated + readme[end:]
    changed = write_if_changed(README_PATH, new_readme)
    if changed:
        print("Updated generated repository and pull-request tables.")
    else:
        print("Generated README section is already current.")

    update_assets(repos, open_count, merged_count, pull_requests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
