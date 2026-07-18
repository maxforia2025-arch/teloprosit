#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🖼 Карточка-обложка к посту канала «Тело просит».

Каждая публикация уходит с картинкой сверху. Картинка не декоративная:
на ней заголовок поста и мотив его рубрики, поэтому в ленте пост читается
ещё до раскрытия текста.

Визуальный код — CHANNEL_BIBLE §5: фон #0F0E14→#1A1822, акцент #D98C7A,
никакой «страшной» медицины. Формат 1080×1350 (4:5) — максимум высоты,
который Telegram отдаёт картинке в ленте.

Только stdlib + внешний растеризатор SVG→PNG (rsvg-convert / cairosvg / Chrome).
Если растеризатора нет, вызывающий код обязан опубликовать пост без картинки:
пропущенная публикация хуже публикации без обложки.

Запуск:
    python3 cards.py                 # карточка к первому посту → card_preview.png
    python3 cards.py --id signal_20  # карточка к конкретному посту
    python3 cards.py --all           # по одной карточке на каждую рубрику
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS_PATH = os.path.join(HERE, "posts.json")
CONFIG_PATH = os.path.join(HERE, "config.json")

W, H = 1080, 1350
BG_TOP, BG_BOT = "#0F0E14", "#1A1822"
ACCENT = "#D98C7A"
TEXT = "#F1EDF5"
MUTED = "#8B8496"
FAM = "Inter, 'Helvetica Neue', Helvetica, 'DejaVu Sans', Arial, sans-serif"
MARGIN = 96

# Рубрика → подпись и мотив. Мотив рисуется вектором: узнаётся с расстояния
# и не тащит за собой ни стоки, ни лицензии.
PILLARS = {
    "Сигнал":           {"label": "СИГНАЛ",           "glyph": "pulse"},
    "Сон и ритм":       {"label": "СОН И РИТМ",       "glyph": "moon"},
    "Простое действие": {"label": "ПРОСТОЕ ДЕЙСТВИЕ", "glyph": "step"},
    "Красный флаг":     {"label": "КРАСНЫЙ ФЛАГ",     "glyph": "flag"},
}
DEFAULT_PILLAR = {"label": "ТЕЛО ПРОСИТ", "glyph": "pulse"}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def wrap(text, per_line):
    """Простой перенос по словам: SVG сам переносить не умеет."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        probe = (cur + " " + w).strip()
        if len(probe) <= per_line:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_title(title):
    """Кегль под длину заголовка: короткий — крупно, длинный — мельче.

    Порог по символам в строке подобран под ширину 1080 минус поля.
    """
    n = len(str(title))
    if n <= 34:
        return 82, 17
    if n <= 60:
        return 70, 21
    if n <= 90:
        return 60, 25
    return 52, 29


def glyph_svg(kind, cx, cy, s):
    """Мотив рубрики. s — характерный размер."""
    if kind == "moon":
        # Полумесяц: внешняя дуга радиусом r, обратная — БОЛЬШИМ радиусом.
        # Радиус меньше половины хорды SVG молча растягивает, и месяц схлопывается
        # в круг — отсюда 1.35, а не «просто чуть меньше».
        r = s * 0.5
        return (
            '<path d="M {x:.0f} {top:.0f} a {r:.0f} {r:.0f} 0 1 0 0 {d:.0f} '
            'a {r2:.0f} {r2:.0f} 0 1 1 0 {nd:.0f} z" fill="{ac}" opacity="0.92"/>'
            '<circle cx="{sx1:.0f}" cy="{sy1:.0f}" r="{sr1:.0f}" fill="{ac}" opacity="0.55"/>'
            '<circle cx="{sx2:.0f}" cy="{sy2:.0f}" r="{sr2:.0f}" fill="{ac}" opacity="0.35"/>'
        ).format(x=cx + r * 0.35, top=cy - r, r=r, d=2 * r,
                 r2=r * 1.35, nd=-2 * r, ac=ACCENT,
                 sx1=cx + s * 0.70, sy1=cy - s * 0.46, sr1=s * 0.075,
                 sx2=cx + s * 0.92, sy2=cy - s * 0.04, sr2=s * 0.05)

    if kind == "step":
        # Круг и стрелка вперёд: одно маленькое действие сегодня.
        r = s * 0.46
        return (
            '<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="none" '
            'stroke="{ac}" stroke-width="{sw:.0f}" opacity="0.85"/>'
            '<path d="M {x1:.0f} {cy:.0f} L {x2:.0f} {cy:.0f} M {x3:.0f} {y3:.0f} '
            'L {x2:.0f} {cy:.0f} L {x3:.0f} {y4:.0f}" fill="none" stroke="{ac}" '
            'stroke-width="{sw:.0f}" stroke-linecap="round" stroke-linejoin="round"/>'
        ).format(cx=cx, cy=cy, r=r, sw=s * 0.075, ac=ACCENT,
                 x1=cx - r * 0.5, x2=cx + r * 0.48,
                 x3=cx + r * 0.12, y3=cy - r * 0.36, y4=cy + r * 0.36)

    if kind == "flag":
        # Флажок на древке: рубрика ведёт к врачу, а не пугает.
        h = s * 0.9
        return (
            '<path d="M {px:.0f} {py:.0f} L {px:.0f} {pb:.0f}" stroke="{ac}" '
            'stroke-width="{sw:.0f}" stroke-linecap="round"/>'
            '<path d="M {px:.0f} {py:.0f} L {fx:.0f} {fy:.0f} L {px:.0f} {fb:.0f} z" '
            'fill="{ac}" opacity="0.92"/>'
        ).format(px=cx - s * 0.28, py=cy - h * 0.5, pb=cy + h * 0.5,
                 fx=cx + s * 0.46, fy=cy - h * 0.16, fb=cy + h * 0.18,
                 ac=ACCENT, sw=s * 0.07)

    # pulse — основной мотив канала
    w = s * 1.25
    x0, y0, amp = cx - w / 2, cy, s * 0.42
    x = lambda t: x0 + w * t
    d = ("M {:.0f} {:.0f} L {:.0f} {:.0f} L {:.0f} {:.0f} L {:.0f} {:.0f} "
         "L {:.0f} {:.0f} L {:.0f} {:.0f}").format(
        x(0.0), y0, x(0.34), y0, x(0.46), y0 + amp * 0.55,
        x(0.56), y0 - amp, x(0.66), y0, x(1.0), y0)
    return ('<path d="' + d + '" fill="none" stroke="' + ACCENT +
            '" stroke-width="{:.0f}" stroke-linecap="round" stroke-linejoin="round"/>'
            .format(s * 0.085) +
            '<circle cx="{:.0f}" cy="{:.0f}" r="{:.0f}" fill="{}"/>'
            .format(x(1.0), y0, s * 0.075, ACCENT))


def build_svg(post, cfg):
    # `label`/`glyph` в самом посте перебивают рубрику — так карточку получает
    # и то, что рубрикой не является (например, еженедельная реклама сети).
    if post.get("label"):
        pillar = {"label": post["label"], "glyph": post.get("glyph", "pulse")}
    else:
        pillar = PILLARS.get(str(post.get("cat", "")).strip(), DEFAULT_PILLAR)
    title = str(post.get("title", "")).strip()
    size, per_line = fit_title(title)
    lines = wrap(title, per_line)

    handle = str(cfg.get("channel_handle", "@teloprosit"))
    name = str(cfg.get("channel_name", "Тело просит"))

    # Блок заголовка прижат к низу: сверху воздух и мотив, как в библии канала.
    line_h = size * 1.24
    block_h = len(lines) * line_h
    title_top = H - MARGIN - 150 - block_h

    body = []
    for i, ln in enumerate(lines):
        body.append(
            '<text x="{x}" y="{y:.0f}" font-family="{f}" font-size="{s}" '
            'font-weight="600" fill="{c}">{t}</text>'.format(
                x=MARGIN, y=title_top + (i + 1) * line_h, f=FAM, s=size,
                c=TEXT, t=esc(ln)))

    return """<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">
      <stop offset="0" stop-color="{bt}"/><stop offset="1" stop-color="{bb}"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.3" r="0.7">
      <stop offset="0" stop-color="{ac}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="{ac}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" fill="url(#halo)"/>

  <text x="{m}" y="{lab_y}" font-family="{f}" font-size="34" font-weight="600"
        fill="{ac}" letter-spacing="6">{label}</text>
  <rect x="{m}" y="{rule_y}" width="96" height="4" fill="{ac}" opacity="0.75"/>

  {glyph}

  {body}

  <text x="{m}" y="{foot_y}" font-family="{f}" font-size="34" font-weight="400"
        fill="{mu}" letter-spacing="2">{name} · {handle}</text>
</svg>
""".format(W=W, H=H, bt=BG_TOP, bb=BG_BOT, ac=ACCENT, mu=MUTED, f=FAM, m=MARGIN,
           lab_y=MARGIN + 46, rule_y=MARGIN + 76,
           label=esc(pillar["label"]),
           glyph=glyph_svg(pillar["glyph"], W / 2, H * 0.36, 300),
           body="\n  ".join(body),
           foot_y=H - MARGIN, name=esc(name), handle=esc(handle))


CHROME = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def render(post, cfg, out_path=None):
    """SVG → PNG. Возвращает путь или None, если растеризатора нет."""
    out_path = out_path or os.path.join(HERE, "card_tmp.png")
    svg_path = os.path.join(HERE, "card_tmp.svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(build_svg(post, cfg))

    if shutil.which("rsvg-convert"):
        r = subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H),
                            "-o", out_path, svg_path], capture_output=True)
        if r.returncode == 0 and os.path.exists(out_path):
            return out_path
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=out_path,
                         output_width=W, output_height=H)
        return out_path
    except Exception:
        pass
    for exe in CHROME:
        if os.path.exists(exe):
            subprocess.run([exe, "--headless", "--disable-gpu", "--hide-scrollbars",
                            "--window-size=" + str(W) + "," + str(H),
                            "--screenshot=" + out_path, "file://" + svg_path],
                           capture_output=True, timeout=90)
            if os.path.exists(out_path):
                return out_path
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="id поста из банка")
    ap.add_argument("--all", action="store_true", help="по карточке на каждую рубрику")
    args = ap.parse_args()

    cfg = json.load(open(CONFIG_PATH, encoding="utf-8"))
    posts = json.load(open(POSTS_PATH, encoding="utf-8"))

    if args.all:
        seen = set()
        for p in posts:
            cat = p.get("cat")
            if cat in seen:
                continue
            seen.add(cat)
            slug = PILLARS.get(cat, DEFAULT_PILLAR)["glyph"]
            out = render(p, cfg, os.path.join(HERE, "card_" + slug + ".png"))
            print(("✓ " + str(out)) if out else "✗ нет растеризатора SVG→PNG")
        return 0

    post = next((p for p in posts if p.get("id") == args.id), posts[0]) if args.id else posts[0]
    out = render(post, cfg, os.path.join(HERE, "card_preview.png"))
    print(("✓ " + out + "  ← " + str(post.get("title"))) if out
          else "✗ не найден растеризатор (rsvg-convert / cairosvg / Chrome)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
