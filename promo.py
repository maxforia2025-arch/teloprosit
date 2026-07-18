#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""📣 Еженедельная перекрёстная реклама сети Maxforia Group в канале «Тело просит».

Правило Президента: одна реклама в неделю, следующий канал по кругу.
Круг задан порядком `order` в promo_channels.json; счётчик недель — в promo_state.json.
Креатив внутри канала меняется на каждом новом круге, чтобы реклама не приедалась.

Защита от дубля: в состоянии хранится ISO-номер недели последней публикации.
Повторный запуск в ту же неделю ничего не отправит — расписание может
сработать дважды (перезапуск воркфлоу, ручной прогон), а слот недельный.

Запуск:
    python3 promo.py                    # DRY-RUN: показать, что уйдёт
    python3 promo.py --send             # опубликовать (нужен BOT_TOKEN)
    python3 promo.py --plan 6           # план на 6 недель вперёд
    python3 promo.py --send --force     # игнорировать недельный слот
"""

import argparse
import datetime
import html
import json
import os
import sys

import post as engine   # переиспользуем load_env / send_telegram / save_json

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNELS_PATH = os.path.join(HERE, "promo_channels.json")
STATE_PATH = os.path.join(HERE, "promo_state.json")
CONFIG_PATH = os.path.join(HERE, "config.json")


def log(msg):
    print("[promo] " + str(msg), flush=True)


def load_state():
    st = engine.load_json(STATE_PATH, {})
    if not isinstance(st, dict):
        st = {}
    st.setdefault("n", 0)          # сколько реклам уже вышло = позиция в круге
    st.setdefault("last_week", "")  # ISO «2026-W29» последней публикации
    return st


def live_channels(cfg):
    excluded = {h.lower() for h in cfg.get("_excluded", {}).get("handles", [])}
    out = [c for c in cfg.get("channels", [])
           if c.get("enabled", True)
           and str(c.get("handle", "")).lower() not in excluded
           and "🔴" not in str(c.get("handle", ""))]
    return sorted(out, key=lambda c: c.get("order", 999))


def pick(channels, n):
    """Канал недели и креатив. Круг по каналам, вариант меняется на новом круге."""
    ch = channels[n % len(channels)]
    variants = ch.get("variants") or [""]
    return ch, variants[(n // len(channels)) % len(variants)]


def format_promo(ch, variant, cfg):
    name = html.escape(str(ch.get("title", "")))
    handle = html.escape(str(ch.get("handle", "")))
    emoji = str(ch.get("emoji", "📣"))
    text = html.escape(str(variant))
    own = html.escape(str(cfg.get("channel_name", "Тело просит")))

    return "\n".join([
        "📣 <b>Что почитать, кроме нас</b>",
        "",
        "Раз в неделю рассказываем про соседний канал — из тех же рук, что и «" + own + "».",
        "",
        emoji + " <b>" + name + "</b>",
        text,
        "",
        "👉 " + handle,
    ])


def iso_week(today=None):
    d = today or datetime.date.today()
    y, w, _ = d.isocalendar()
    return str(y) + "-W" + str(w).zfill(2)


def main():
    ap = argparse.ArgumentParser(description="Еженедельная кросс-реклама сети")
    ap.add_argument("--send", action="store_true", help="реально опубликовать")
    ap.add_argument("--force", action="store_true", help="игнорировать недельный слот")
    ap.add_argument("--plan", type=int, metavar="N", help="показать план на N недель")
    args = ap.parse_args()

    engine.load_env()
    cfg = engine.load_json(CONFIG_PATH, {})
    net = engine.load_json(CHANNELS_PATH, {})
    channels = live_channels(net)
    if not channels:
        log("в сети нет ни одного канала для рекламы")
        return 1

    state = load_state()
    n = int(state.get("n", 0))

    if args.plan:
        log("круг: " + str(len(channels)) + " каналов, одна реклама в неделю")
        for i in range(args.plan):
            ch, _ = pick(channels, n + i)
            log("  неделя +" + str(i) + ": " + str(ch.get("title")) + " " + str(ch.get("handle")))
        return 0

    week = iso_week()
    if state.get("last_week") == week and not args.force:
        log("на неделе " + week + " реклама уже выходила (" +
            str(state.get("last_id", "?")) + "). Слот занят — выхожу.")
        return 0

    ch, variant = pick(channels, n)
    text = format_promo(ch, variant, cfg)

    if not args.send:
        print("\n" + "=" * 56 + "\n" + text + "\n" + "=" * 56)
        log("DRY-RUN: ничего не отправлено. Канал недели: " + str(ch.get("title")))
        return 0

    token = os.environ.get("BOT_TOKEN", "").strip()
    chat = os.environ.get("CHANNEL_ID", "").strip() or str(cfg.get("channel_handle", "")).strip()
    if not token or not chat:
        log("ОШИБКА: не задан BOT_TOKEN" + ("" if chat else " и хендл канала") + ".")
        return 2

    engine.send_telegram(token, chat, text)
    log("опубликована реклама: " + str(ch.get("title")) + " " + str(ch.get("handle")))

    state["n"] = n + 1
    state["last_week"] = week
    state["last_id"] = ch.get("id")
    state["last_run"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    engine.save_json(STATE_PATH, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
