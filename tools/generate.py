#!/usr/bin/env python3
"""Generates the animated SVGs for the profile README from public GitHub data."""
import re, json, os, textwrap, datetime as dt, urllib.request
from xml.sax.saxutils import escape as E

USER = "yatharth2soni"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)
F = "font-family=\"'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace\""
GLOW = ('<filter id="g" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "readme-gen"}), timeout=30).read().decode("utf8", "ignore")

def save(name, body, w, h, defs=""):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {F}>'
           f'<defs>{GLOW}{defs}</defs>{body}</svg>')
    open(os.path.join(OUT, name), "w", encoding="utf8").write(svg)

# ---------------------------------------------------------------- data
TODAY = dt.date.today()
STAMP = dt.datetime.now(dt.timezone.utc).strftime("%d %b %H:%M UTC")
days, totals = {}, {}
for y in range(2022, TODAY.year + 1):
    try:
        t = get(f"https://github.com/users/{USER}/contributions?from={y}-01-01&to={y}-12-31")
    except Exception:
        continue
    ids = {m[1]: (m[0], int(m[2])) for m in re.findall(r'data-date="([\d-]+)"\s+id="([^"]+)"\s+data-level="(\d)"', t)}
    for tid, txt in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', t):
        if tid in ids:
            k = re.match(r"(\d+) contribution", txt.strip())
            days[ids[tid][0]] = (int(k.group(1)) if k else 0, ids[tid][1])
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+" + str(y), t)
    totals[y] = int(m.group(1).replace(",", "")) if m else 0
if not days:
    raise SystemExit("could not fetch contribution data")

LANGS = {"TypeScript": 5, "Python": 3, "JavaScript": 2, "C++": 1}   # fallback: primary language per repo
try:
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100"))
    c = {}
    for r in repos:
        if r.get("language"): c[r["language"]] = c.get(r["language"], 0) + 1
    if c: LANGS = c
except Exception:
    pass

PRS = [  # (repo, title, blurb, number, state, url)
 ("agy-powerline", "Catppuccin Macchiato theme", "Added the Catppuccin Macchiato dark theme, including palette registration, tests, and documentation updates.", 36, "MERGED", "https://github.com/wassim-azi/agy-powerline/pull/36"),
 ("label-checker", "Copilot session instructions", "Updated GitHub Copilot session instructions to run npm ci before making changes or running checks.", 732, "MERGED", "https://github.com/agilepathway/label-checker/pull/732"),
 ("freeCodeCamp", "Curriculum quiz fix", "Fixed spacing in a curriculum quiz question.", 71054, "MERGED", "https://github.com/freeCodeCamp/freeCodeCamp/pull/71054"),
 ("OpenSRE", "Remote agent checks", "Worked on remote-agent connection checks, timeout handling, security protections, and tests.", 88, "OPEN", "https://github.com/swapnildahiphale/OpenSRE/pull/88"),
]
STACK = ["C++", "C", "Java", "Python", "JavaScript", "TypeScript", "React", "Node.js", "NestJS", "PostgreSQL", "MySQL", "Git", "GitHub", "VS Code"]
PROJECTS = [
 ("Khanan Suraksha", "A bilingual mining-safety and governance platform for reporting, inspections, compliance workflows, and geo-tagged field observations.", "SIH", f"https://github.com/{USER}/final_sih", "React · NestJS · PostgreSQL · PostGIS"),
 ("CF Ally", "A competitive-programming analytics dashboard focused on contest trends, performance insights, topic coverage, and problem-solving consistency.", "ANALYTICS", f"https://github.com/{USER}/CF_ally", "React · TypeScript · Chart.js"),
]

# ---------------------------------------------------------------- cards
def card(name, w, h, badge, title, desc, foot, delay):
    lines = textwrap.wrap(desc, int((w - 44) / 7.3))[:3]
    txt = "".join(f'<text x="22" y="{92 + i*20}" fill="#d0d0d0" font-size="12">{E(l)}</text>' for i, l in enumerate(lines))
    solid = badge in ("MERGED", "SIH", "ANALYTICS")
    body = (f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="#000" stroke="#fff" stroke-opacity=".55"/>'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="none" stroke="#fff" stroke-width="2.5" pathLength="100" stroke-dasharray="14 86" filter="url(#g)">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="-100" dur="7s" begin="{delay}s" repeatCount="indefinite"/></rect>'
            f'<rect x="22" y="20" width="{len(badge)*7.4+34}" height="22" rx="11" fill="none" stroke="#fff"/>'
            f'<circle cx="35" cy="31" r="3" fill="#fff"{"" if solid else ""}><animate attributeName="opacity" values="1;.2;1" dur="{1.6 if not solid else 3}s" repeatCount="indefinite"/></circle>'
            f'<text x="45" y="35" fill="#fff" font-size="10.5">{badge}</text>'
            f'<text x="22" y="68" fill="#fff" font-size="16" font-weight="700">{E(title)}</text>{txt}'
            f'<text x="22" y="{h-18}" fill="#fff" font-size="12">{E(foot)}</text>')
    save(name, body, w, h)

for i, (repo, t, d, n, st, url) in enumerate(PRS):
    card(f"oss-{i+1}.svg", 470, 170, st, repo, d, f"{'Merged' if st=='MERGED' else 'Open'} PR #{n} ↗", i * 1.1)
for i, (t, d, b, url, tech) in enumerate(PROJECTS):
    card(f"project-{i+1}.svg", 470, 170, b, t, d, tech, i * 1.3)

# ---------------------------------------------------------------- stack chips
x, y, rows, parts = 0, 0, [], []
W = 960
for i, s in enumerate(STACK):
    cw = int(len(s) * 8.6 + 34)
    if x + cw > W - 32: x, y = 0, y + 46
    parts.append(f'<g transform="translate({x+2},{y+4})"><rect width="{cw}" height="34" rx="8" fill="#000" stroke="#fff" stroke-opacity=".5"/>'
                 f'<rect width="{cw}" height="34" rx="8" fill="none" stroke="#fff" stroke-width="1.6" filter="url(#g)" opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.12;.3;1" dur="7s" begin="{i*0.45:.2f}s" repeatCount="indefinite"/></rect>'
                 f'<text x="{cw/2}" y="22" fill="#fff" font-size="13" text-anchor="middle">{E(s)}</text></g>')
    x += cw + 12
save("stack.svg", f'<rect width="{W}" height="{y+46}" rx="12" fill="#000"/><g transform="translate(14 8)">'+"".join(parts)+"</g>", W, y + 62)

# ---------------------------------------------------------------- stats strip
merged = sum(1 for p in PRS if p[4] == "MERGED")
last_year_start = TODAY - dt.timedelta(days=364)
ly = sum(v[0] for d, v in days.items() if last_year_start.isoformat() <= d <= TODAY.isoformat())
active = sum(1 for d, v in days.items() if v[0] > 0)
stats = [(str(sum(totals.values())), "total contributions"), (str(ly), "in the last year"), (str(len(PRS)), "pull requests"), (str(merged), "merged"), (str(active), "active days")]
cw = 960 / len(stats); body = ""
for i, (v, l) in enumerate(stats):
    cx = cw * i + cw / 2
    body += (f'<text x="{cx}" y="52" fill="#fff" font-size="38" font-weight="700" text-anchor="middle" filter="url(#g)"><animate attributeName="opacity" values="1;.6;1" dur="4s" begin="{i*.5}s" repeatCount="indefinite"/>{v}</text>'
             f'<text x="{cx}" y="80" fill="#c8c8c8" font-size="12" text-anchor="middle">{l}</text>')
    if i: body += f'<line x1="{cw*i}" y1="22" x2="{cw*i}" y2="86" stroke="#fff" stroke-opacity=".35"/>'
body = '<rect x="1" y="1" width="958" height="108" rx="10" fill="#000" stroke="#fff" stroke-opacity=".55"/>' + body
save("stats.svg", body, 960, 110)

# ---------------------------------------------------------------- yearly bars
yrs = sorted(totals); mx = max(totals.values()) or 1
w, h, bw = 470, 260, 52; body = '<rect x="1" y="1" width="468" height="258" rx="10" fill="#000" stroke="#fff" stroke-opacity=".55"/><text x="22" y="32" fill="#fff" font-size="13" font-weight="700">contributions / year</text>'
gap = (w - 44 - bw * len(yrs)) / max(len(yrs) - 1, 1)
for i, yv in enumerate(yrs):
    v = totals[yv]; bh = max(2, 150 * v / mx); bx = 22 + i * (bw + gap); by = 210 - bh
    body += (f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{bh:.1f}" rx="3" fill="#fff" filter="url(#g)"><animate attributeName="height" values="2;{bh:.1f};{bh:.1f};2" keyTimes="0;.25;.85;1" dur="8s" repeatCount="indefinite"/>'
             f'<animate attributeName="y" values="208;{by:.1f};{by:.1f};208" keyTimes="0;.25;.85;1" dur="8s" repeatCount="indefinite"/></rect>'
             f'<text x="{bx+bw/2:.1f}" y="{by-8:.1f}" fill="#fff" font-size="12" text-anchor="middle">{v}</text>'
             f'<text x="{bx+bw/2:.1f}" y="234" fill="#c8c8c8" font-size="12" text-anchor="middle">{yv}</text>')
body += '<line x1="22" y1="210" x2="448" y2="210" stroke="#fff" stroke-opacity=".5"/>'
save("years.svg", body, w, h)

# ---------------------------------------------------------------- languages
tot = sum(LANGS.values()); items = sorted(LANGS.items(), key=lambda kv: -kv[1])[:6]
body = '<rect x="1" y="1" width="468" height="258" rx="10" fill="#000" stroke="#fff" stroke-opacity=".55"/><text x="22" y="32" fill="#fff" font-size="13" font-weight="700">most-used languages</text>'
for i, (n, c) in enumerate(items):
    pct = c / tot * 100; yy = 66 + i * 36; bwid = 426 * pct / 100
    body += (f'<text x="22" y="{yy}" fill="#fff" font-size="12">{E(n)}</text><text x="448" y="{yy}" fill="#c8c8c8" font-size="12" text-anchor="end">{pct:.0f}%</text>'
             f'<rect x="22" y="{yy+8}" width="426" height="6" rx="3" fill="#1a1a1a"/>'
             f'<rect x="22" y="{yy+8}" width="{bwid:.1f}" height="6" rx="3" fill="#fff" filter="url(#g)"><animate attributeName="width" values="0;{bwid:.1f};{bwid:.1f};0" keyTimes="0;.25;.85;1" dur="8s" begin="{i*.2}s" repeatCount="indefinite"/></rect>')
body += f'<text x="22" y="246" fill="#8a8a8a" font-size="10">// by primary language of {tot} repositories</text>'
save("langs.svg", body, 470, 260)

# ---------------------------------------------------------------- heatmap
end = TODAY; start = end - dt.timedelta(days=end.weekday() + 1 if end.weekday() != 6 else 0) - dt.timedelta(weeks=52)
body = '<rect x="1" y="1" width="958" height="188" rx="10" fill="#000" stroke="#fff" stroke-opacity=".55"/>'
body += f'<text x="22" y="30" fill="#fff" font-size="13" font-weight="700">{ly} contributions in the last year</text><circle cx="690" cy="26" r="4" fill="#39d353"><animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/><animate attributeName="r" values="3;6;3" dur="1.4s" repeatCount="indefinite"/></circle><text x="704" y="30" fill="#39d353" font-size="11">LIVE · synced {STAMP}</text>'
fill = {0: ("#0d1410", 0), 1: ("#0e4429", 0), 2: ("#006d32", 0), 3: ("#26a641", 0), 4: ("#39d353", 1)}
d = start; col = 0; lastm = None; k = 0
while d <= end:
    row = (d.weekday() + 1) % 7
    if row == 0 and d != start: col += 1
    cx, cy = 52 + col * 15.5, 50 + row * 17
    if d.month != lastm and row == 0:
        body += f'<text x="{cx}" y="46" fill="#9a9a9a" font-size="10">{d.strftime("%b")}</text>'; lastm = d.month
    lv = days.get(d.isoformat(), (0, 0))[1]; f, g = fill[lv]
    extra = ""
    if lv:
        extra = f'<animate attributeName="opacity" values="1;.35;1" dur="3.2s" begin="{(k%13)*.25:.2f}s" repeatCount="indefinite"/>'; k += 1
    body += f'<rect x="{cx:.1f}" y="{cy}" width="12" height="12" rx="2.5" fill="{f}" stroke="#17261d" stroke-width=".6"{" filter=\"url(#g)\"" if lv>=3 else ""}>{extra}</rect>'
    d += dt.timedelta(days=1)
for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")): body += f'<text x="22" y="{50+r*17+10}" fill="#9a9a9a" font-size="10">{n}</text>'
body += '<rect x="52" y="0" width="60" height="188" fill="url(#sw)" opacity=".18"><animate attributeName="x" values="-80;900" dur="6s" repeatCount="indefinite"/></rect>'
body += '<text x="740" y="176" fill="#9a9a9a" font-size="10">less</text>' + "".join(f'<rect x="{768+i*16}" y="166" width="11" height="11" rx="2.5" fill="{fill[i][0]}" stroke="#17261d" stroke-width=".6"/>' for i in range(5)) + '<text x="854" y="176" fill="#9a9a9a" font-size="10">more</text>'
save("heatmap.svg", body, 960, 190, '<linearGradient id="sw" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')

# ---------------------------------------------------------------- connect buttons (animated icons)
GH = "M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.54-3.87-1.54-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.24 3.34.95.1-.74.4-1.24.72-1.53-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.58.23 2.75.11 3.04.74.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z"
ICON = {
 "github": f'<path d="{GH}" fill="#fff" transform="translate(-12 -12)"/>',
 "linkedin": '<rect x="-11" y="-11" width="22" height="22" rx="4" fill="none" stroke="#fff" stroke-width="2"/><circle cx="-5.5" cy="-5.5" r="1.7" fill="#fff"/><path d="M-5.5 -1V7M-1 7V-1M-1 2.5C-1 -1 6 -1.5 6 2.5V7" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',
 "opensource": '<circle cx="-6" cy="-7" r="2.6" fill="none" stroke="#fff" stroke-width="2"/><circle cx="-6" cy="7" r="2.6" fill="none" stroke="#fff" stroke-width="2"/><circle cx="7" cy="-1" r="2.6" fill="none" stroke="#fff" stroke-width="2"/><path d="M-6 -4.4V4.4M7 1.6C7 6 -6 2 -6 4.4" fill="none" stroke="#fff" stroke-width="2"/>',
}
def button(name, key, label, sub, delay):
    w = 300
    body = (f'<rect x="1" y="1" width="{w-2}" height="62" rx="12" fill="#000" stroke="#fff" stroke-opacity=".55"/>'
            f'<rect x="1" y="1" width="{w-2}" height="62" rx="12" fill="none" stroke="#fff" stroke-width="2.5" pathLength="100" stroke-dasharray="12 88" filter="url(#g)"><animate attributeName="stroke-dashoffset" from="0" to="-100" dur="5s" begin="{delay}s" repeatCount="indefinite"/></rect>'
            f'<g transform="translate(40 32)"><circle r="17" fill="none" stroke="#fff" stroke-opacity=".7"><animate attributeName="r" values="16;25;16" dur="2.4s" begin="{delay}s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0;.9" dur="2.4s" begin="{delay}s" repeatCount="indefinite"/></circle>'
            f'<g filter="url(#g)"><animateTransform attributeName="transform" type="scale" values="1;1.14;1" dur="2.4s" begin="{delay}s" repeatCount="indefinite"/>{ICON[key]}</g></g>'
            f'<text x="78" y="28" fill="#fff" font-size="15" font-weight="700">{label}</text><text x="78" y="47" fill="#c0c0c0" font-size="12">{E(sub)}</text>'
            f'<text x="{w-26}" y="38" fill="#fff" font-size="15" text-anchor="end">↗<animate attributeName="x" values="{w-26};{w-20};{w-26}" dur="1.6s" repeatCount="indefinite"/></text>')
    save(name, body, w, 64)
button("btn-github.svg", "github", "GitHub", f"@{USER}", 0)
button("btn-linkedin.svg", "linkedin", "LinkedIn", "Connect with me", .8)
button("btn-opensource.svg", "opensource", "Open Source", "Pull requests", 1.6)

# ---------------------------------------------------------------- text panels (black in any theme)
def panel(name, cmd, tag, lines, extra_h=0, bullets=False):
    h = 100 + len(lines) * (30 if bullets else 24) + extra_h
    b = (f'<rect x="1" y="1" width="958" height="{h-2}" rx="12" fill="#000" stroke="#fff" stroke-opacity=".55"/>'
         f'<text x="26" y="42" fill="#fff" font-size="17" font-weight="700" filter="url(#g)">❯ {E(cmd)}</text>'
         f'<text x="934" y="42" fill="#c8c8c8" font-size="11" text-anchor="end">{tag}</text>'
         f'<line x1="26" y1="60" x2="934" y2="60" stroke="#fff" stroke-width="1.5" stroke-dasharray="910" filter="url(#g)"><animate attributeName="stroke-dashoffset" values="910;0;0;910" keyTimes="0;.2;.85;1" dur="9s" repeatCount="indefinite"/></line>')
    for i, l in enumerate(lines):
        yy = 92 + i * (30 if bullets else 24)
        b += f'<text x="26" y="{yy}" fill="#e6e6e6" font-size="13.5">{E(l)}<animate attributeName="opacity" values="0;1;1;.75;1" keyTimes="0;.1;.5;.75;1" dur="9s" begin="{i*.25}s" repeatCount="indefinite"/></text>'
    save(name, b, 960, h)
def head(name, cmd, tag):
    b = (f'<rect x="1" y="1" width="958" height="52" rx="12" fill="#000" stroke="#fff" stroke-opacity=".55"/>'
         f'<text x="26" y="34" fill="#fff" font-size="17" font-weight="700" filter="url(#g)">❯ {E(cmd)}</text>'
         f'<text x="934" y="33" fill="#c8c8c8" font-size="11" text-anchor="end">{tag}</text>'
         f'<rect x="1" y="49" width="958" height="3" fill="url(#sw)"><animate attributeName="x" values="-300;960" dur="4s" repeatCount="indefinite"/></rect>')
    save(name, b, 960, 54, '<linearGradient id="sw" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
panel("about.svg", "cat about.md", "ABOUT", [
 "I'm a Computer Science student who enjoys solving problems, building software,",
 "and learning by contributing to real-world codebases.", "",
 "[+] Improving my Data Structures & Algorithms and software engineering skills",
 "[+] Interested in web development, backend systems, and AI/ML",
 "[+] Learning open source through issues, pull requests, reviews, tests, and docs",
 "[+] Approach: build consistently, learn from reviews, and keep improving"])
panel("focus.svg", "cat focus.txt", "CURRENT FOCUS", [
 "[+] Practicing data structures & algorithms (DSA)", "[+] Solving problems consistently and learning patterns",
 "[+] Building full-stack projects", "[+] Improving tests, documentation and maintainability",
 "[+] Learning from reviews and contributing upstream"])
for n, c, t in [("toolkit", "ls ./toolkit", "TECH STACK"), ("oss", "ls ./open-source", "MERGED & OPEN PRs"), ("projects", "ls ./projects", "PROJECTS"), ("stats", "github --stats", "ACTIVITY"), ("connect", "Let's connect", "LINKS")]:
    head(f"h-{n}.svg", c, t)
save("divider.svg", '<rect width="960" height="10" fill="#000"/><line x1="0" y1="5" x2="960" y2="5" stroke="#fff" stroke-opacity=".4"/><rect y="4" width="240" height="2" fill="url(#s)" filter="url(#g)"><animate attributeName="x" values="-240;960" dur="3.5s" repeatCount="indefinite"/></rect>', 960, 10,
     '<linearGradient id="s" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')

# ---------------------------------------------------------------- auto-scrolling terminal window
def tx(x, y, s, size=13, fill="#e6e6e6", anchor="start", weight=400, extra=""):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{E(s)}</text>'
def cmdpill(y, s):
    w = len(s) * 9.6 + 74
    return (f'<rect x="0.5" y="{y}" width="{w:.1f}" height="38" rx="10" fill="#050505" stroke="#fff" stroke-opacity=".8"/>'
            + tx(16, y + 25, "$", 16, "#8a8a8a") + tx(36, y + 25, "❯ " + s, 16, "#fff", "start", 700, 'filter="url(#g)"'))
els = []; add = els.append
items = [("GITHUB", "YATHARTH2SONI"), ("LINKEDIN", "CONNECT"), ("REPOSITORIES", "EXPLORE")]
wd = [len(a) * 9 + 12 + len(b) * 9.4 + 28 for a, b in items]
bx = (904 - sum(wd) - 28 * 2) / 2
for (a, b), w_ in zip(items, wd):
    lw, vw = len(a) * 9 + 12, len(b) * 9.4 + 28
    add(tx(bx, 40, a, 12, "#fff", "start", 500, 'letter-spacing="1.5"') + f'<rect x="{bx+lw:.1f}" y="20" width="{vw:.1f}" height="30" rx="3" fill="#fff"/>' + tx(bx + lw + vw / 2, 40, b, 12, "#000", "middle", 700, 'letter-spacing="1.5"'))
    bx += w_ + 28
add(tx(452, 125, "YATHARTH SONI", 44, "#fff", "middle", 700, 'filter="url(#g)" letter-spacing="2"'))
add(tx(452, 158, "> Open Source Contributor", 16, "#fff", "middle", 500))
add(tx(452, 190, "Khanan Suraksha & CF Ally Builder", 19, "#fff", "middle", 700))
add('<line x1="60" y1="215" x2="844" y2="215" stroke="#fff" stroke-opacity=".6"/>')
# about
A = 240; add(cmdpill(A, "cat about.md")); yy = A + 74
for l in textwrap.wrap("I'm a Computer Science student who enjoys solving problems, building software, and learning by contributing to real-world codebases.", 104):
    add(tx(0, yy, l, 14)); yy += 26
yy += 8
for l in ["Improving my Data Structures & Algorithms and software engineering skills", "Interested in web development, backend systems, and AI/ML",
          "Learning open source through issues, pull requests, reviews, tests, and docs", "Approach: build consistently, learn from reviews, and keep improving"]:
    add(tx(0, yy, "[+]", 13.5, "#fff", "start", 700) + tx(40, yy, l, 13.5, "#d8d8d8")); yy += 26
# toolkit
B = yy + 30; add(cmdpill(B, "ls ./toolkit")); cx, cy = 0, B + 62
for i, sname in enumerate(STACK):
    cw = int(len(sname) * 8.6 + 34)
    if cx + cw > 904: cx, cy = 0, cy + 46
    add(f'<g transform="translate({cx},{cy})"><rect width="{cw}" height="34" rx="8" fill="#050505" stroke="#fff" stroke-opacity=".6"/>'
        f'<rect width="{cw}" height="34" rx="8" fill="none" stroke="#fff" stroke-width="1.6" filter="url(#g)" opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.12;.3;1" dur="7s" begin="{i*.45:.2f}s" repeatCount="indefinite"/></rect>'
        + tx(cw / 2, 22, sname, 13, "#fff", "middle") + '</g>')
    cx += cw + 12
# projects
C = cy + 34 + 46; add(cmdpill(C, "ls ./projects"))
for j, (ttl, desc, bdg, url, tech) in enumerate(PROJECTS):
    x0, y0 = j * 464, C + 62
    add(f'<g transform="translate({x0},{y0})"><rect x=".5" y=".5" width="439" height="160" rx="10" fill="#050505" stroke="#fff" stroke-opacity=".6"/>'
        f'<rect x=".5" y=".5" width="439" height="160" rx="10" fill="none" stroke="#fff" stroke-width="2.5" pathLength="100" stroke-dasharray="14 86" filter="url(#g)"><animate attributeName="stroke-dashoffset" from="0" to="-100" dur="7s" begin="{j*1.3}s" repeatCount="indefinite"/></rect>'
        f'<rect x="20" y="18" width="{len(bdg)*7.4+34:.0f}" height="22" rx="11" fill="none" stroke="#fff"/><circle cx="33" cy="29" r="3" fill="#fff"><animate attributeName="opacity" values="1;.2;1" dur="3s" repeatCount="indefinite"/></circle>'
        + tx(43, 33, bdg, 10.5, "#fff") + tx(20, 66, ttl, 16, "#fff", "start", 700)
        + "".join(tx(20, 90 + k_ * 19, l, 12, "#cfcfcf") for k_, l in enumerate(textwrap.wrap(desc, 54)[:3])) + tx(20, 148, tech, 12, "#fff") + '</g>')
# contributions
D = C + 62 + 160 + 44; add(cmdpill(D, "git log ./contributions")); cw5 = 904 / len(stats)
for i, (v, l) in enumerate(stats):
    cxm = cw5 * i + cw5 / 2
    add(tx(cxm, D + 90, v, 32, "#fff", "middle", 700, 'filter="url(#g)"') + tx(cxm, D + 114, l, 12, "#bdbdbd", "middle"))
    if i: add(f'<line x1="{cw5*i:.1f}" y1="{D+62}" x2="{cw5*i:.1f}" y2="{D+122}" stroke="#fff" stroke-opacity=".3"/>')
yy = D + 160; add(tx(0, yy, "# pull requests", 12, "#8a8a8a")); yy += 28
for repo, ttl, _d, n, st, _u in PRS:
    if st == "MERGED": add(f'<rect x="0" y="{yy-15}" width="78" height="22" rx="4" fill="#fff"/>' + tx(39, yy, "MERGED", 11, "#000", "middle", 700))
    else: add(f'<rect x="0" y="{yy-15}" width="78" height="22" rx="4" fill="none" stroke="#fff"><animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></rect>' + tx(39, yy, "OPEN", 11, "#fff", "middle", 700))
    add(tx(98, yy, repo, 14, "#fff", "start", 700) + tx(260, yy, f"#{n}", 13, "#bdbdbd") + tx(340, yy, ttl, 13, "#d8d8d8")); yy += 32
yy += 14; add(tx(0, yy, "# contribution heatmap · last 12 months", 12, "#8a8a8a") + f'<circle cx="318" cy="{yy-4}" r="4" fill="#39d353"><animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/></circle>' + tx(330, yy, f"LIVE · synced {STAMP}", 12, "#39d353")); H0 = yy + 14
end = TODAY; st0 = end - dt.timedelta(days=end.weekday() + 1 if end.weekday() != 6 else 0) - dt.timedelta(weeks=52)
dd = st0; colh = 0; kk = 0; lastm = None
while dd <= end:
    row = (dd.weekday() + 1) % 7
    if row == 0 and dd != st0: colh += 1
    lv = days.get(dd.isoformat(), (0, 0))[1]; fcol = {0: "#0d1410", 1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#39d353"}[lv]
    if row == 0 and dd.month != lastm: add(tx(40 + colh * 15.5, H0 - 4, dd.strftime("%b"), 10, "#8a8a8a")); lastm = dd.month
    anim = ""
    if lv: anim = f'<animate attributeName="opacity" values="1;.35;1" dur="3.2s" begin="{(kk%13)*.25:.2f}s" repeatCount="indefinite"/>'; kk += 1
    add(f'<rect x="{40+colh*15.5:.1f}" y="{H0+row*17}" width="12" height="12" rx="2.5" fill="{fcol}" stroke="#17261d" stroke-width=".6"{" filter=&quot;url(#g)&quot;" if lv>=3 else ""}>{anim}</rect>'.replace("&quot;", '"'))
    dd += dt.timedelta(days=1)
for r_, n_ in ((1, "Mon"), (3, "Wed"), (5, "Fri")): add(tx(0, H0 + r_ * 17 + 10, n_, 10, "#8a8a8a"))
# focus
E_ = H0 + 7 * 17 + 40; add(cmdpill(E_, "cat focus.txt")); yy = E_ + 74
for l in ["Practicing data structures & algorithms (DSA)", "Solving problems consistently and learning patterns", "Building full-stack projects", "Improving tests, documentation and maintainability", "Learning from reviews and contributing upstream"]:
    add(tx(0, yy, "[+]", 13.5, "#fff", "start", 700) + tx(40, yy, l, 13.5, "#d8d8d8")); yy += 28
add(tx(0, yy + 28, "$", 16, "#8a8a8a") + f'<rect x="22" y="{yy+14}" width="10" height="20" fill="#fff"><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.45;.5;.95;1" dur="1s" repeatCount="indefinite"/></rect>')
add(f'<rect x="0.5" y="{yy+56}" width="903" height="122" rx="10" fill="#0a0a0a" stroke="#2f2f2f"/>' + tx(20, yy + 86, "text", 12, "#7a7a7a") + tx(884, yy + 86, "terminal specification", 12, "#7a7a7a", "end") + f'<line x1="1" y1="{yy+100}" x2="903" y2="{yy+100}" stroke="#2f2f2f"/>' + tx(20, yy + 148, "[EOF] ─── guest@yatharth2soni:~$ logout ─── Connection to terminal closed.", 15.5, "#fff"))
F_ = yy + 206
VY, VH = 108, 502; maxoff = F_ - VH
stops = [0] + [min(m - 16, maxoff) for m in (A, B, C, D, E_)]
# timeline
hold0, trn, hold, upd = 2.0, 1.2, 2.8, 2.6
pts = [(0, 0), (hold0, 0)]; cur = hold0; holds = []; downs = []
for i, s_ in enumerate(stops[1:]):
    ts = cur; cur += trn; pts.append((cur, s_)); downs.append((ts, cur)); cur += hold; pts.append((cur, s_)); holds.append((i, ts, cur))
up_s = cur; cur += upd; pts.append((cur, 0)); cur += 0.6; pts.append((cur, 0)); total = cur
kt = ";".join(f"{p/total:.4f}" for p, _ in pts)
spl = ";".join("0 0 1 1" if pts[i][1] == pts[i+1][1] else "0.45 0 0.2 1" for i in range(len(pts) - 1))
def scroll_anim(f): return f'<animateTransform attributeName="transform" type="translate" values="{";".join(f(y_) for _, y_ in pts)}" keyTimes="{kt}" calcMode="spline" keySplines="{spl}" dur="{total}s" repeatCount="indefinite"/>'
def disc(intervals):
    ks, vs = [0.0], ["0"]
    for a_, b_ in intervals: ks += [a_ / total, b_ / total]; vs += ["1", "0"]
    return f'<animate attributeName="opacity" values="{";".join(vs)}" keyTimes="{";".join(f"{k:.4f}" for k in ks)}" calcMode="discrete" dur="{total}s" repeatCount="indefinite"/>'
body = ('<rect x="4" y="4" width="952" height="612" rx="16" fill="#000" stroke="#fff" stroke-opacity=".6" stroke-width="1.5" filter="url(#g)"><animate attributeName="stroke-opacity" values=".9;.45;.9" dur="3s" repeatCount="indefinite"/></rect>'
        '<rect x="4" y="4" width="952" height="612" rx="16" fill="none" stroke="#fff" stroke-width="3.5" pathLength="100" stroke-dasharray="12 88" filter="url(#g)"><animate attributeName="stroke-dashoffset" from="0" to="-100" dur="6s" repeatCount="indefinite"/></rect>'
        '<circle cx="34" cy="30" r="7" fill="#fff"/><circle cx="58" cy="30" r="7" fill="#9a9a9a"/><circle cx="82" cy="30" r="7" fill="#4a4a4a"/>'
        + tx(110, 35, "guest@yatharth2soni:", 13, "#9a9a9a") + tx(262, 35, "~/profile/README.md", 14, "#fff", "start", 700)
        + '<rect x="470" y="14" width="128" height="32" rx="7" fill="none" stroke="#fff" stroke-opacity=".6"/>' + tx(534, 35, "Terminal Shell", 12, "#d0d0d0", "middle")
        + '<rect x="610" y="14" width="116" height="32" rx="7" fill="#fff" filter="url(#g)"/>' + tx(668, 35, "✦ Glow Lights", 12, "#000", "middle", 700)
        + '<rect x="738" y="14" width="112" height="32" rx="7" fill="none" stroke="#fff" stroke-opacity=".8"/><path d="M757 24 L757 36 L767 30 Z" fill="#fff"><animate attributeName="opacity" values="1;.25;1" dur="1.4s" repeatCount="indefinite"/></path>' + tx(802, 35, "Auto-Scroll", 12, "#fff", "middle") + '<circle cx="838" cy="30" r="3.5" fill="#39d353" filter="url(#g)"><animate attributeName="opacity" values="1;.2;1" dur="1s" repeatCount="indefinite"/></circle>'
        + '<rect x="862" y="14" width="34" height="32" rx="7" fill="none" stroke="#fff" stroke-opacity=".6"/>' + tx(879, 36, "↑", 16, "#fff", "middle")
        + '<rect x="908" y="14" width="34" height="32" rx="7" fill="none" stroke="#fff" stroke-opacity=".6"/>' + tx(925, 36, "↓", 16, "#fff", "middle")
        + f'<g opacity="0">{disc([(up_s, up_s+upd)])}<rect x="862" y="14" width="34" height="32" rx="7" fill="#fff"/>' + tx(879, 36, "↑", 16, "#000", "middle", 700) + '</g>'
        + f'<g opacity="0">{disc(downs)}<rect x="908" y="14" width="34" height="32" rx="7" fill="#fff"/>' + tx(925, 36, "↓", 16, "#000", "middle", 700) + '</g>'
        + '<line x1="5" y1="56" x2="955" y2="56" stroke="#fff" stroke-opacity=".5"/><line x1="5" y1="104" x2="955" y2="104" stroke="#fff" stroke-opacity=".5"/>'
        + tx(28, 86, "✦ Jump:", 12, "#9a9a9a"))
jx = 104
for i, lab in enumerate(["cat about.md", "ls ./toolkit", "ls ./projects", "git log ./contributions", "cat focus.txt"]):
    w_ = len(lab) * 7.3 + 46; _, a_, b_ = holds[i]
    body += (f'<rect x="{jx}" y="68" width="{w_:.0f}" height="28" rx="6" fill="none" stroke="#fff" stroke-opacity=".5"/>' + tx(jx + 14, 87, "❯ " + lab, 12, "#d0d0d0")
             + f'<g opacity="0">{disc([(a_, b_)])}<rect x="{jx}" y="68" width="{w_:.0f}" height="28" rx="6" fill="#fff" filter="url(#g)"/>' + tx(jx + 14, 87, "❯ " + lab, 12, "#000", "start", 700) + '</g>')
    jx += w_ + 10
body += (f'<g clip-path="url(#vp)"><g transform="translate(28 {VY})">{scroll_anim(lambda y_: f"28 {VY-y_:.1f}")}{"".join(els)}</g>'
         f'<rect x="944" y="{VY+8}" width="4" height="{VH-16}" rx="2" fill="#fff" opacity=".12"/>'
         f'<rect x="944" y="{VY+8}" width="4" height="70" rx="2" fill="#fff" filter="url(#g)"><animateTransform attributeName="transform" type="translate" values="{";".join(f"0 {y_/maxoff*(VH-16-70):.1f}" for _, y_ in pts)}" keyTimes="{kt}" calcMode="spline" keySplines="{spl}" dur="{total}s" repeatCount="indefinite"/></rect></g>')
save("terminal.svg", body, 960, 620, f'<clipPath id="vp"><rect x="6" y="{VY}" width="948" height="{VH}"/></clipPath>')
print("terminal height", F_, "maxoff", maxoff, "loop", total)

EOFTXT = "[EOF] ─── guest@yatharth2soni:~$ logout ─── Connection to terminal closed."
fb = ('<rect x="1" y="1" width="958" height="148" rx="12" fill="#0a0a0a" stroke="#fff" stroke-opacity=".35"/>'
      '<rect x="1" y="1" width="958" height="148" rx="12" fill="none" stroke="#fff" stroke-width="2.5" pathLength="100" stroke-dasharray="10 90" filter="url(#g)"><animate attributeName="stroke-dashoffset" from="0" to="-100" dur="8s" repeatCount="indefinite"/></rect>'
      + tx(28, 40, "text", 14, "#7a7a7a") + tx(932, 40, "terminal specification", 14, "#7a7a7a", "end")
      + '<line x1="1" y1="62" x2="959" y2="62" stroke="#fff" stroke-opacity=".2"/>'
      + '<clipPath id="rv"><rect x="20" y="78" width="0" height="50"><animate attributeName="width" values="0;900;900;0" keyTimes="0;.4;.9;1" dur="10s" repeatCount="indefinite"/></rect></clipPath>'
      + f'<g clip-path="url(#rv)">{tx(28, 112, EOFTXT, 18.5, "#fff", "start", 500, chr(102)+"ilter=" + chr(34) + "url(#g)" + chr(34))}</g>'
      + '<rect x="28" y="94" width="11" height="24" fill="#fff"><animate attributeName="x" values="28;876;876;28" keyTimes="0;.4;.9;1" dur="10s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.45;.5;.95;1" dur="1s" repeatCount="indefinite" additive="replace"/></rect>')
save("footer.svg", fb, 960, 150)
print("ok", totals, "last-year", ly, "active", active, LANGS)
