#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🫀 Оформление канала «Тело просит»: ставит аватар и описание через бота.

Зачем скрипт, а не руки: аватар генерируется кодом (`make_avatar.py`), и
переставить его после правки бренда должно быть одним кликом, а не ритуалом.

Токен нигде не светится: локально — `.env` (в .gitignore), в облаке —
GitHub Secrets. В коде секретов нет.

Требование Telegram: бот должен быть админом канала с правом
«Изменение профиля канала» (Change channel info). Без него API вернёт
"not enough rights" — это единственная частая причина отказа.

Запуск:
    python3 set_profile.py                # DRY-RUN: показать, что будет поставлено
    python3 set_profile.py --send         # поставить аватар + описание
    python3 set_profile.py --send --photo-only
    python3 set_profile.py --send --description-only
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
ENV_PATH = os.path.join(HERE, ".env")
PHOTO_PATH = os.path.join(HERE, "avatar.png")
API = "https://api.telegram.org/bot"
# Лимит Telegram на описание канала. Длиннее — API молча отрежет, поэтому режем сами и предупреждаем.
DESC_LIMIT = 255


def log(msg):
    print("[telo_prosit] " + str(msg), flush=True)


def load_env():
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_call(token, method, fields=None, files=None):
    """POST в Bot API. files={'photo': (имя, байты)} → multipart вручную, без зависимостей."""
    url = API + token + "/" + method
    if not files:
        data = urllib.parse.urlencode(fields or {}).encode("utf-8")
        req = urllib.request.Request(url, data=data)
    else:
        boundary = "----teloprosit7f3d9a1c"
        body = b""
        for key, val in (fields or {}).items():
            body += ("--" + boundary + "\r\n").encode()
            body += ('Content-Disposition: form-data; name="' + key + '"\r\n\r\n').encode()
            body += str(val).encode("utf-8") + b"\r\n"
        for key, (fname, blob) in files.items():
            body += ("--" + boundary + "\r\n").encode()
            body += ('Content-Disposition: form-data; name="' + key + '"; filename="' + fname + '"\r\n').encode()
            body += b"Content-Type: image/png\r\n\r\n" + blob + b"\r\n"
        body += ("--" + boundary + "--\r\n").encode()
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)

    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    if not out.get("ok"):
        raise RuntimeError(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="реально применить (иначе dry-run)")
    ap.add_argument("--photo-only", action="store_true")
    ap.add_argument("--description-only", action="store_true")
    args = ap.parse_args()

    load_env()
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)

    desc = str(cfg.get("description", "")).strip()
    if len(desc) > DESC_LIMIT:
        log("описание длиннее " + str(DESC_LIMIT) + " символов — обрезаю, поправь config.json")
        desc = desc[:DESC_LIMIT]

    do_photo = not args.description_only
    do_desc = not args.photo_only and bool(desc)

    if do_photo and not os.path.exists(PHOTO_PATH):
        log("нет avatar.png — сначала: python3 make_avatar.py")
        return 1

    log("канал: " + str(os.environ.get("CHANNEL_ID") or cfg.get("channel_handle")))
    if do_photo:
        log("аватар: " + PHOTO_PATH + " (" + str(os.path.getsize(PHOTO_PATH) // 1024) + " КБ)")
    if do_desc:
        log("описание (" + str(len(desc)) + " симв.):\n" + desc)

    if not args.send:
        log("DRY-RUN: ничего не изменено. Повтори с --send.")
        return 0

    token = os.environ.get("BOT_TOKEN", "").strip()
    chat = os.environ.get("CHANNEL_ID", "").strip() or str(cfg.get("channel_handle", "")).strip()
    if not token or not chat:
        log("нет BOT_TOKEN или CHANNEL_ID в окружении")
        return 1

    try:
        if do_photo:
            with open(PHOTO_PATH, "rb") as fh:
                api_call(token, "setChatPhoto", {"chat_id": chat},
                         {"photo": ("avatar.png", fh.read())})
            log("✅ аватар канала обновлён")
        if do_desc:
            api_call(token, "setChatDescription", {"chat_id": chat, "description": desc})
            log("✅ описание канала обновлено")
    except RuntimeError as exc:
        detail = str(exc)
        log("✗ Telegram отказал: " + detail)
        if "not enough rights" in detail or "CHAT_ADMIN_REQUIRED" in detail:
            log("→ дай боту в канале право «Изменение профиля канала» и запусти снова")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
