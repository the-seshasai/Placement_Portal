"""Notification abstraction so the delivery channel can be swapped (email,
SMS, ...) without touching task logic. Only a Google Chat incoming webhook
is implemented for now, per the brief — simplest thing to demo locally."""

import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class Notifier:
    def send(self, message: str) -> bool:
        raise NotImplementedError


class GoogleChatNotifier(Notifier):
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send(self, message: str) -> bool:
        try:
            resp = requests.post(self.webhook_url, json={"text": message}, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException:
            logger.exception("Failed to send Google Chat notification")
            return False


class LoggingNotifier(Notifier):
    """Fallback when no webhook is configured — logs instead of failing, so
    the scheduled job still runs cleanly on a machine with no webhook set up."""

    def send(self, message: str) -> bool:
        logger.info("[notification] %s", message)
        return True


def get_notifier():
    webhook_url = current_app.config.get("GOOGLE_CHAT_WEBHOOK_URL")
    if webhook_url:
        return GoogleChatNotifier(webhook_url)
    return LoggingNotifier()
