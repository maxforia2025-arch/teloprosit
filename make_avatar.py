#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🫀 Аватар канала «Тело просит» — чистый вектор, без внешних зависимостей.

Визуальный код из CHANNEL_BIBLE §5: фон #0F0E14→#1A1822, акцент #D98C7A,
текст #F1EDF5, много воздуха, ноль «страшной» медицины.

Символ: пульсовая волна, у которой один зубец мягко переходит в каплю-точку —
«тело подаёт сигнал». Читается в круглом кропе Telegram даже в списке чатов.

Пишет avatar.svg + avatar.png (640×640, круглый кроп) и
avatar_wide.svg/.png (баннер 1280×640 с названием) — для шапок и обложек.

Запуск:
    python3 make_avatar.py            # собрать SVG и отрендерить PNG
    python3 make_avatar.py --svg-only # только SVG (если нет Chrome)
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

BG_TOP = "#0F0E14"
BG_BOT = "#1A1822"
ACCENT = "#D98C7A"
TEXT = "#F1EDF5"
MUTED = "#8B8496"


def defs(rx=0.5, ry=0.42):
    return f'''  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0" stop-color="{BG_TOP}"/>
      <stop offset="1" stop-color="{BG_BOT}"/>
    </linearGradient>
    <radialGradient id="halo" cx="{rx}" cy="{ry}" r="0.62">
      <stop offset="0"    stop-color="{ACCENT}" stop-opacity="0.20"/>
      <stop offset="0.55" stop-color="{ACCENT}" stop-opacity="0.05"/>
      <stop offset="1"    stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="pulse" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0"    stop-color="{ACCENT}" stop-opacity="0.35"/>
      <stop offset="0.30" stop-color="{ACCENT}" stop-opacity="1"/>
      <stop offset="1"    stop-color="{ACCENT}" stop-opacity="1"/>
    </linearGradient>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="7" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>'''


def pulse_path(x0, y0, w, amp):
    """Волна: ровная линия → мягкий подъём → резкий зубец → возврат к линии.

    Зубец намеренно один: канал говорит про ОДИН сигнал за раз.
    """
    x = lambda t: x0 + w * t
    return (
        f"M {x(0.00):.1f} {y0:.1f} "
        f"L {x(0.26):.1f} {y0:.1f} "
        f"C {x(0.32):.1f} {y0:.1f} {x(0.33):.1f} {y0 - amp*0.30:.1f} {x(0.37):.1f} {y0 - amp*0.30:.1f} "
        f"L {x(0.44):.1f} {y0 - amp*0.30:.1f} "
        f"L {x(0.52):.1f} {y0 + amp*0.52:.1f} "
        f"L {x(0.60):.1f} {y0 - amp:.1f} "
        f"L {x(0.68):.1f} {y0:.1f} "
        f"L {x(1.00):.1f} {y0:.1f}"
    )


def build_square(size=640):
    c = size / 2
    # Поля с запасом: Telegram режет аватар в круг, край не должен цеплять смысл.
    pw = size * 0.64
    px = c - pw / 2
    py = c
    amp = size * 0.19
    d = pulse_path(px, py, pw, amp)
    dot_r = size * 0.032

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
{defs()}
  <rect width="{size}" height="{size}" fill="url(#bg)"/>
  <rect width="{size}" height="{size}" fill="url(#halo)"/>

  <!-- дыхательные кольца: тело в покое -->
  <circle cx="{c}" cy="{c}" r="{size*0.375:.1f}" fill="none" stroke="{ACCENT}" stroke-opacity="0.14" stroke-width="{size*0.004:.1f}"/>
  <circle cx="{c}" cy="{c}" r="{size*0.305:.1f}" fill="none" stroke="{ACCENT}" stroke-opacity="0.07" stroke-width="{size*0.004:.1f}"/>

  <!-- сигнал -->
  <path d="{d}" fill="none" stroke="url(#pulse)" stroke-width="{size*0.030:.1f}"
        stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
  <circle cx="{px + pw:.1f}" cy="{py:.1f}" r="{dot_r:.1f}" fill="{ACCENT}" filter="url(#glow)"/>
</svg>
'''


def build_wide(w=1280, h=640):
    cy = h / 2
    pw = w * 0.30
    px = w * 0.085
    py = cy + h * 0.10
    amp = h * 0.155
    d = pulse_path(px, py, pw, amp)
    tx = px + pw + w * 0.075

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
{defs(rx=0.22, ry=0.5)}
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <rect width="{w}" height="{h}" fill="url(#halo)"/>

  <path d="{d}" fill="none" stroke="url(#pulse)" stroke-width="{h*0.028:.1f}"
        stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>
  <circle cx="{px + pw:.1f}" cy="{py:.1f}" r="{h*0.030:.1f}" fill="{ACCENT}" filter="url(#glow)"/>

  <text x="{tx:.0f}" y="{cy - h*0.02:.0f}"
        font-family="Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
        font-size="{h*0.145:.0f}" font-weight="600" fill="{TEXT}"
        letter-spacing="{h*0.004:.1f}">Тело просит</text>
  <text x="{tx:.0f}" y="{cy + h*0.085:.0f}"
        font-family="Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
        font-size="{h*0.058:.0f}" font-weight="400" fill="{MUTED}"
        letter-spacing="{h*0.006:.1f}">Тело говорит первым</text>
</svg>
'''


CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]


def find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return shutil.which("chromium") or shutil.which("google-chrome")


def render_png(svg_path, png_path, w, h):
    """SVG → PNG. rsvg-convert / cairosvg, иначе headless Chrome."""
    if shutil.which("rsvg-convert"):
        r = subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(h),
                            "-o", png_path, svg_path], capture_output=True)
        if r.returncode == 0 and os.path.exists(png_path):
            return "rsvg-convert"
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path,
                         output_width=w, output_height=h)
        return "cairosvg"
    except Exception:
        pass

    chrome = find_chrome()
    if not chrome:
        return None
    tmp = os.path.join(HERE, "_shot")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                    "--default-background-color=00000000",
                    "--force-device-scale-factor=1",
                    "--window-size=" + str(w) + "," + str(h),
                    "--screenshot=" + png_path,
                    "file://" + svg_path], capture_output=True, timeout=90)
    shutil.rmtree(tmp, ignore_errors=True)
    return "chrome" if os.path.exists(png_path) else None


def write(name, svg, w, h, svg_only):
    svg_path = os.path.join(HERE, name + ".svg")
    with open(svg_path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print("SVG  → " + svg_path)
    if svg_only:
        return
    png_path = os.path.join(HERE, name + ".png")
    how = render_png(svg_path, png_path, w, h)
    if how:
        print("PNG  → " + png_path + "  (" + how + ", " + str(w) + "×" + str(h) + ")")
    else:
        print("PNG  ✗ не найден конвертер (rsvg-convert / cairosvg / Chrome) — остался SVG")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg-only", action="store_true")
    args = ap.parse_args()
    write("avatar", build_square(640), 640, 640, args.svg_only)
    write("avatar_wide", build_wide(1280, 640), 1280, 640, args.svg_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
