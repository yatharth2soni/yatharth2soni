#!/usr/bin/env python3
"""Generate a compact, readable one-shot circular reveal for the README header.

Only the header is animated. Projects, PR links, tables and charts live in the
Markdown below the GIF, so they remain readable, selectable and clickable.
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 960, 340
WHITE = (250, 250, 250)
SOFT = (224, 224, 224)
MUTED = (146, 146, 146)
BG = (2, 2, 2)


def _font(size: int, bold: bool = False, sans: bool = False):
    if sans:
        candidates = (
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
            if bold else
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
        )
    else:
        candidates = (
            ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf"]
            if bold else
            ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]
        )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _center(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill=WHITE) -> None:
    draw.text((WIDTH // 2, y), text, font=font, fill=fill, anchor="mt")


def _background() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 40):
        draw.line((x, 0, x, HEIGHT), fill=(12, 12, 12), width=1)
    for y in range(0, HEIGHT, 40):
        draw.line((0, y, WIDTH, y), fill=(12, 12, 12), width=1)
    return image


def generate_intro_gif(output_path: str | Path, open_count: int = 2, merged_count: int = 3, pr_rows=None) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = _background()
    draw = ImageDraw.Draw(base)

    # Double boundary, with a clean terminal title bar.
    draw.rounded_rectangle((12, 12, WIDTH - 13, HEIGHT - 13), radius=12, outline=(120, 120, 120), width=1)
    draw.rounded_rectangle((17, 17, WIDTH - 18, HEIGHT - 18), radius=9, outline=(220, 220, 220), width=1)
    draw.ellipse((36, 32, 45, 41), fill=WHITE)
    draw.text((56, 27), "README.md / profile", font=_font(12), fill=SOFT, anchor="lt")
    draw.text((WIDTH - 82, 27), "UTF-8", font=_font(11), fill=SOFT, anchor="lt")
    draw.line((36, 54, WIDTH - 36, 54), fill=(105, 105, 105), width=1)

    draw.text((42, 76), "$ whoami", font=_font(15, bold=True), fill=SOFT, anchor="lt")
    title = "YATHARTH SONI"
    title_font = _font(54, bold=True, sans=True)
    title_box = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_box[2] - title_box[0]
    title_x = (WIDTH - title_width) // 2 - 13
    draw.text((title_x, 106), title, font=title_font, fill=WHITE, anchor="lt", stroke_width=1, stroke_fill=WHITE)
    cx = title_x + title_width + 8
    draw.rounded_rectangle((cx, 116, cx + 9, 164), radius=1, fill=WHITE)

    _center(draw, 177, "BTech CSE student", _font(23, bold=True, sans=True), WHITE)
    _center(draw, 216, "I build practical projects, explore real codebases,", _font(14), SOFT)
    _center(draw, 239, "and contribute fixes, tests, themes and documentation.", _font(14), SOFT)
    _center(draw, 282, "DSA  /  PROBLEM SOLVING  /  PROJECTS  /  OPEN SOURCE", _font(12, bold=True), WHITE)

    # Small terminal motif, decorative only; actionable links are actual Markdown below.
    mx, my = WIDTH - 66, 94
    draw.line((mx - 20, my, mx, my + 20, mx - 20, my + 40), fill=WHITE, width=3, joint="curve")
    draw.line((mx + 5, my + 45, mx + 32, my + 45), fill=WHITE, width=3)

    # The circle reveals ONLY this header. Keep the rest of the README as live Markdown.
    outside = _background()
    frames: list[Image.Image] = []
    durations: list[int] = []
    max_radius = int(math.hypot(WIDTH / 2, HEIGHT / 2)) + 8
    radii = [2, 3, 5]
    for i in range(1, 32):
        t = i / 31
        ease = 1 - (1 - t) ** 3  # quick start, smooth finish
        radii.append(5 + (max_radius - 5) * ease)
    radii.extend([max_radius + 3, max_radius + 6, max_radius + 2, max_radius])

    cx0, cy0 = WIDTH // 2, HEIGHT // 2
    for idx, radius_f in enumerate(radii):
        radius = int(round(radius_f))
        mask = Image.new("L", (WIDTH, HEIGHT), 0)
        ImageDraw.Draw(mask).ellipse((cx0 - radius, cy0 - radius, cx0 + radius, cy0 + radius), fill=255)
        frame = Image.composite(base, outside, mask).convert("RGBA")

        # Bright white travelling boundary with a restrained glow.
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pulse = 0.85 + 0.15 * math.sin(idx / max(1, len(radii) - 1) * math.pi)
        gd.ellipse((cx0 - radius, cy0 - radius, cx0 + radius, cy0 + radius), outline=(255, 255, 255, int(230 * pulse)), width=5)
        frame = Image.alpha_composite(frame, glow.filter(ImageFilter.GaussianBlur(12)))
        hard = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        ImageDraw.Draw(hard).ellipse((cx0 - radius, cy0 - radius, cx0 + radius, cy0 + radius), outline=(255, 255, 255, 255), width=2)
        frame = Image.alpha_composite(frame, hard).convert("RGB")
        frames.append(frame)
        if idx == 0:
            durations.append(180)
        elif idx < 3:
            durations.append(60)
        elif idx >= len(radii) - 4:
            durations.append(85)
        else:
            durations.append(45)

    # Hold the clean completed header for a moment, then the GIF stops on the final frame.
    frames.append(frames[-1].copy())
    durations.append(2200)
    quantized = [frame.quantize(colors=48, method=Image.Quantize.MEDIANCUT) for frame in frames]
    quantized[0].save(output_path, save_all=True, append_images=quantized[1:], duration=durations,
                      optimize=True, disposal=2)


if __name__ == "__main__":
    generate_intro_gif(Path(__file__).resolve().parent.parent / "assets" / "profile-intro.gif")
