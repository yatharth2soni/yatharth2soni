#!/usr/bin/env python3
"""Render the self-hosted, circle-reveal summary GIF used at the top of README.md."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 960, 1040
CENTER = (480, 520)
FINAL_RADIUS = 460
WHITE = (247, 247, 247)
SOFT = (208, 208, 208)
MUTED = (145, 145, 145)
PANEL = (4, 4, 4)
LINE = (120, 120, 120)


def _font(size: int, bold: bool = False, sans: bool = False) -> ImageFont.ImageFont:
    paths = []
    if sans:
        if bold:
            paths += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
        else:
            paths += ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    else:
        if bold:
            paths += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf"]
        else:
            paths += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _center_text(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.ImageFont, fill=WHITE, stroke_width: int = 0):
    draw.text((WIDTH // 2, y), text, font=font, fill=fill, anchor="mt", stroke_width=stroke_width, stroke_fill=(0, 0, 0))


def _fit_font(text: str, max_width: int, start_size: int, min_size: int = 11, bold: bool = False, sans: bool = False):
    for size in range(start_size, min_size - 1, -1):
        f = _font(size, bold=bold, sans=sans)
        box = f.getbbox(text)
        if box[2] - box[0] <= max_width:
            return f
    return _font(min_size, bold=bold, sans=sans)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _grid_background() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (2, 2, 2))
    d = ImageDraw.Draw(img)
    for x in range(0, WIDTH, 48):
        d.line((x, 0, x, HEIGHT), fill=(12, 12, 12), width=1)
    for y in range(0, HEIGHT, 48):
        d.line((0, y, WIDTH, y), fill=(12, 12, 12), width=1)
    # The central canvas is just a shade brighter than the surrounding screen.
    d.ellipse((CENTER[0]-FINAL_RADIUS+6, CENTER[1]-FINAL_RADIUS+6,
               CENTER[0]+FINAL_RADIUS-6, CENTER[1]+FINAL_RADIUS-6), fill=(3, 3, 3))
    for x in range(0, WIDTH, 48):
        d.line((x, CENTER[1]-FINAL_RADIUS+6, x, CENTER[1]+FINAL_RADIUS-6), fill=(13, 13, 13), width=1)
    for y in range(CENTER[1]-FINAL_RADIUS+6, CENTER[1]+FINAL_RADIUS-6, 48):
        d.line((CENTER[0]-FINAL_RADIUS+6, y, CENTER[0]+FINAL_RADIUS-6, y), fill=(13, 13, 13), width=1)
    return img


def _draw_section_heading(draw: ImageDraw.ImageDraw, y: int, command: str, tag: str | None = None) -> None:
    font = _font(15, bold=True)
    dy = abs(y - CENTER[1])
    half = math.sqrt(max(0, FINAL_RADIUS**2 - dy**2))
    left_edge = max(76, int(CENTER[0] - half + 20))
    right_edge = min(900, int(CENTER[0] + half - 20))
    draw.text((left_edge, y), "❯", font=font, fill=WHITE, anchor="lm")
    command_x = left_edge + 23
    draw.text((command_x, y), command, font=font, fill=WHITE, anchor="lm")
    command_right = draw.textbbox((command_x, y), command, font=font, anchor="lm")[2]
    if tag:
        tag_font = _font(9)
        tag_w = draw.textbbox((0, 0), tag.upper(), font=tag_font)[2]
        tag_x = right_edge - tag_w
        draw.text((tag_x, y), tag.upper(), font=tag_font, fill=SOFT, anchor="lm")
        end = tag_x - 16
    else:
        end = right_edge
    if end > command_right + 14:
        draw.line((command_right + 12, y, end, y), fill=(117, 117, 117), width=1)


def _draw_card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, status: str, lines: Iterable[str], tech: str) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=6, fill=(3, 3, 3), outline=(188, 188, 188), width=1)
    draw.text((x1 + 16, y1 + 14), status, font=_font(9), fill=MUTED, anchor="lt")
    draw.text((x1 + 16, y1 + 37), title, font=_fit_font(title, x2-x1-32, 15, bold=True), fill=WHITE, anchor="lt")
    linefont = _font(10)
    yy = y1 + 64
    for line in lines:
        draw.text((x1 + 16, yy), line, font=linefont, fill=SOFT, anchor="lt")
        yy += 15
    draw.line((x1+16, y2-28, x2-16, y2-28), fill=(90, 90, 90), width=1)
    draw.text((x1+16, y2-19), tech, font=_fit_font(tech, x2-x1-32, 9, min_size=8), fill=MUTED, anchor="lt")


def _status_rows(pr_rows: list[dict] | None, merged_count: int, open_count: int) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for pr in pr_rows or []:
        repo = str(pr.get("repo") or "").strip()
        number = pr.get("number")
        state = str(pr.get("status") or "").upper()
        if not repo or not number or state not in {"OPEN", "MERGED", "CLOSED"}:
            continue
        if any(token in repo.lower() for token in ("leetcode", "codeforces")):
            continue
        label = f"{repo} #{number}  ·  {state}"
        if label not in seen:
            rows.append(label)
            seen.add(label)
        if len(rows) >= 5:
            break
    if not rows:
        rows = [
            "Merged upstream contributions",
            "Public PR status is refreshed by GitHub Actions",
        ]
    return rows


def generate_intro_gif(output_path: str | Path, open_count: int = 2, merged_count: int = 3, pr_rows: list[dict] | None = None) -> None:
    """Create a one-shot circle expansion that reveals a compact profile dashboard.

    The graphic is an animated summary. Links and live detailed lists remain in the
    Markdown below it because GIF text itself is not clickable.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base = _grid_background()
    draw = ImageDraw.Draw(base)

    # Header metadata and command prompt.
    draw.ellipse((260, 122, 267, 129), fill=WHITE)
    draw.text((279, 117), "README.md / profile", font=_font(11), fill=SOFT, anchor="lt")
    draw.text((660, 117), "UTF-8", font=_font(10), fill=SOFT, anchor="lt")
    draw.line((260, 145, 700, 145), fill=(130, 130, 130), width=1)
    draw.text((260, 166), "$ whoami", font=_font(12), fill=SOFT, anchor="lt")

    title = "YATHARTH SONI"
    title_font = _fit_font(title, 690, 48, min_size=40, bold=True, sans=True)
    draw.text((480, 194), title, font=title_font, fill=WHITE, anchor="mt", stroke_width=1, stroke_fill=(255,255,255))
    cursor_x = 480 + (draw.textbbox((0, 0), title, font=title_font)[2] / 2) + 10
    draw.rounded_rectangle((int(cursor_x), 203, int(cursor_x + 9), 249), radius=1, fill=WHITE)
    _center_text(draw, 254, "BTech CSE student", _font(19, bold=True, sans=True), fill=WHITE)

    intro_font = _font(11)
    _center_text(draw, 292, "I build practical projects, explore real codebases,", intro_font, fill=SOFT)
    _center_text(draw, 312, "and contribute fixes, tests and documentation.", intro_font, fill=SOFT)
    _center_text(draw, 348, "DSA  /  PROBLEM SOLVING  /  PROJECTS  /  OPEN SOURCE", _font(10), fill=WHITE)

    # Projects: only project work, not external coding-profile tiles.
    _draw_section_heading(draw, 391, "ls ./projects", "SELECTED WORK")
    _draw_card(
        draw, (55, 410, 472, 531), "Khanan Suraksha", "PROJECT / 01",
        ["Bilingual mining-safety and", "governance reporting platform."],
        "React · NestJS · PostgreSQL · PostGIS",
    )
    _draw_card(
        draw, (488, 410, 905, 531), "CF Ally", "PROJECT / 02",
        ["Programming analytics for contest", "trends and problem-solving insights."],
        "React · TypeScript · Chart.js",
    )

    # Live open-source status summary.
    _draw_section_heading(draw, 563, "git log --oneline ./contributions", "OPEN SOURCE")
    rows = _status_rows(pr_rows, merged_count, open_count)
    # Always show recent PR entries first; remaining slots use an honest total summary.
    visible_rows = rows[:5]
    row_font = _fit_font("label-checker #732  ·  MERGED", 730, 11, min_size=10)
    for i, row in enumerate(visible_rows):
        y = 593 + i * 25
        if y > 710:
            break
        draw.text((130, y), ">", font=_font(11), fill=SOFT, anchor="lt")
        draw.text((153, y), row, font=row_font, fill=WHITE if "OPEN" in row else SOFT, anchor="lt")
    summary_y = 722
    summary = f"{merged_count} MERGED  /  {open_count} OPEN  ·  PUBLIC PR ACTIVITY"
    _center_text(draw, summary_y, summary, _fit_font(summary, 600, 10), fill=MUTED)

    _draw_section_heading(draw, 766, "cat focus.txt", "CURRENT FOCUS")
    focus = [
        "[+] Practicing data structures & algorithms (DSA)",
        "[+] Solving problems consistently and learning patterns",
        "[+] Building projects and improving code quality",
    ]
    for i, row in enumerate(focus):
        draw.text((190, 793 + i * 24), row, font=_fit_font(row, 585, 10, min_size=9), fill=SOFT, anchor="lt")

    footer = "github.com/yatharth2soni  /  linkedin.com/in/yatharth-soni"
    _center_text(draw, 889, footer, _fit_font(footer, 520, 9, min_size=8), fill=MUTED)

    # A slightly dimmer outer screen remains outside the circle; the bright circle
    # clips/reveals the whole dashboard as it grows, rather than only the header text.
    outside = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    od = ImageDraw.Draw(outside)
    for x in range(0, WIDTH, 48):
        od.line((x, 0, x, HEIGHT), fill=(7, 7, 7), width=1)
    for y in range(0, HEIGHT, 48):
        od.line((0, y, WIDTH, y), fill=(7, 7, 7), width=1)

    frames: list[Image.Image] = []
    durations: list[int] = []
    # Give the opening dot a brief beat, then expand with a smooth cubic easing.
    radii = [2, 3, 4]
    for i in range(1, 43):
        t = i / 42
        ease = t * t * (3 - 2 * t)
        radii.append(4 + (FINAL_RADIUS - 4) * ease)
    # A restrained white-light pulse as the boundary reaches full size.
    radii.extend([FINAL_RADIUS + 3, FINAL_RADIUS + 5, FINAL_RADIUS + 2, FINAL_RADIUS])

    for index, radius_f in enumerate(radii):
        radius = int(round(radius_f))
        mask = Image.new("L", (WIDTH, HEIGHT), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse((CENTER[0]-radius, CENTER[1]-radius, CENTER[0]+radius, CENTER[1]+radius), fill=255)
        frame = Image.composite(base, outside, mask).convert("RGBA")

        # Soft halo on the outside of the rim, with a white hard edge at the rim.
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pulse = 0.88 + 0.12 * math.sin(min(index / max(1, len(radii)-1), 1) * math.pi)
        bbox = (CENTER[0]-radius, CENTER[1]-radius, CENTER[0]+radius, CENTER[1]+radius)
        gd.ellipse(bbox, outline=(255, 255, 255, int(225*pulse)), width=6)
        soft_glow = glow.filter(ImageFilter.GaussianBlur(17))
        frame = Image.alpha_composite(frame, soft_glow)
        mid = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        ImageDraw.Draw(mid).ellipse(bbox, outline=(255, 255, 255, int(190*pulse)), width=3)
        frame = Image.alpha_composite(frame, mid)
        sharp = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        ImageDraw.Draw(sharp).ellipse(bbox, outline=(255, 255, 255, 255), width=2)
        frame = Image.alpha_composite(frame, sharp).convert("RGB")
        frames.append(frame)
        if index < 3:
            durations.append(180 if index == 0 else 55)
        elif index >= len(radii)-4:
            durations.append(90)
        else:
            durations.append(48)

    # Hold the fully revealed dashboard so the visitor can read the summary.
    frames.append(frames[-1].copy())
    durations.append(1800)

    # Quantize consistently to GIF to reduce the payload but retain bright white edges.
    quantized = [im.quantize(colors=64, method=Image.Quantize.MEDIANCUT) for im in frames]
    quantized[0].save(
        output_path,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        optimize=True,
        disposal=2,
        # No loop extension: GIF plays once and stops on the final dashboard.
    )


if __name__ == "__main__":
    generate_intro_gif(Path(__file__).resolve().parent.parent / "assets" / "profile-intro.gif")
