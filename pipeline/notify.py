"""Alerts to your phone via a Telegram bot. Falls back to the log if no bot is set up."""
import os

import requests

from .common import log, secret


def run_link() -> str | None:
    server, repo, run = (os.environ.get(k) for k in
                         ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    return f"{server}/{repo}/actions/runs/{run}" if server and repo and run else None


def send(text: str) -> None:
    token, chat = secret("TELEGRAM_BOT_TOKEN"), secret("TELEGRAM_CHAT_ID")
    link = run_link()
    if link:
        text += f"\n\nRun details and files: {link}"
    if not token or not chat:
        log.info("ALERT (no Telegram set up):\n%s", text)
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
                      timeout=20).raise_for_status()
    except Exception as e:
        log.warning("Telegram alert failed: %s", e)
