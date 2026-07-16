"""Telegram Bot API delivery with secrets supplied only by environment."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from npe.infrastructure.database import Database

TelegramTransport = Callable[[str, dict[str, str]], dict[str, object]]


@dataclass(frozen=True)
class TelegramDeliveryResult:
    sent: int
    failed: int


class TelegramNotifier:
    def __init__(
        self,
        database: Database,
        token: str | None,
        chat_id: str | None,
        transport: TelegramTransport | None = None,
        proxy_url: str | None = None,
    ) -> None:
        self.database = database
        self.token = token
        self.chat_id = chat_id
        self.proxy_url = proxy_url
        self.transport = transport or self._request

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def dispatch_pending(self) -> TelegramDeliveryResult:
        if not self.configured:
            return TelegramDeliveryResult(0, 0)
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT i.*, b.code, p.name AS project_name
                   FROM intervention_events i
                   JOIN buildings b ON b.id = i.building_id
                   JOIN projects p ON p.id = i.project_id
                   WHERE i.channel = 'telegram' AND i.status = 'pending'
                     AND i.notify_attempts < 2
                   ORDER BY i.created_at"""
            ).fetchall()
        sent = 0
        failed = 0
        for row in rows:
            status = {
                "missing_reference": "MissingReference",
                "needs_review": "NeedsReview",
                "captcha": "Captcha/Login intervention",
                "approval_ready": "Approval ready",
                "completed": "Completed",
            }.get(str(row["kind"]), str(row["kind"]))
            text = (
                "Near Project Environment\n"
                f"Project: {row['project_name']}\n"
                f"Building: {row['code']}\n"
                f"Status: {status}\n"
                "Action: open the project dashboard for details."
            )
            try:
                response = self.transport(
                    "sendMessage", {"chat_id": str(self.chat_id), "text": text}
                )
                if response.get("ok") is not True:
                    raise RuntimeError("Telegram returned an unsuccessful response")
            except (OSError, RuntimeError, ValueError):
                with self.database.connect() as connection:
                    connection.execute(
                        """UPDATE intervention_events
                           SET notify_attempts = notify_attempts + 1,
                               last_notify_error = 'telegram_delivery_failed'
                           WHERE id = ? AND status = 'pending'""",
                        (str(row["id"]),),
                    )
                failed += 1
                continue
            with self.database.connect() as connection:
                connection.execute(
                    """UPDATE intervention_events SET status = 'notified', notified_at = ?,
                       notify_attempts = notify_attempts + 1, last_notify_error = NULL
                       WHERE id = ? AND status = 'pending'""",
                    (self._utc_now(), str(row["id"])),
                )
            sent += 1
        return TelegramDeliveryResult(sent, failed)

    def send_test_message(self) -> bool:
        if not self.configured:
            return False
        response = self.transport(
            "sendMessage",
            {"chat_id": str(self.chat_id), "text": "Near Project Environment: test OK"},
        )
        return response.get("ok") is True

    def discover_chat_id(self) -> str | None:
        if not self.token:
            return None
        response = self.transport("getUpdates", {})
        results = response.get("result")
        if not isinstance(results, list):
            return None
        for update in reversed(results):
            if not isinstance(update, dict):
                continue
            message = update.get("message")
            if isinstance(message, dict):
                chat = message.get("chat")
                if isinstance(chat, dict) and "id" in chat:
                    return str(chat["id"])
        return None

    def _request(self, method: str, payload: dict[str, str]) -> dict[str, object]:
        assert self.token is not None
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(payload).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {"http": self.proxy_url, "https": self.proxy_url}
                    if self.proxy_url else {}
                )
            )
            with opener.open(request, timeout=20) as response:
                value = json.loads(response.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            raise OSError("Telegram request failed; credentials were redacted") from error
        if not isinstance(value, dict):
            raise ValueError("Telegram response must be an object")
        return value

    @staticmethod
    def _utc_now() -> str:
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()
