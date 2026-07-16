"""One-time local Telegram setup; secrets never pass through source or logs."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import winreg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TelegramSetup(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Near Project Environment — Telegram Setup")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste the NEW BotFather token below. It is never logged."))
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("New Telegram bot token")
        layout.addWidget(self.token)
        self.configure = QPushButton("Configure and discover /start chat")
        self.configure.clicked.connect(self.run_setup)
        layout.addWidget(self.configure)
        self.status = QLabel("Send /start to the bot before configuring.")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)

    def run_setup(self) -> None:
        token = self.token.text().strip()
        if not token:
            self.status.setText("Token is required.")
            return
        self.configure.setEnabled(False)
        QApplication.processEvents()
        try:
            chat_id = discover_chat_id(token)
            if chat_id is None:
                self.status.setText("No /start message found. Send /start and try again.")
                return
            save_user_environment("NPE_TELEGRAM_BOT_TOKEN", token)
            save_user_environment("NPE_TELEGRAM_CHAT_ID", chat_id)
            self.token.clear()
            self.status.setText(
                f"Configured successfully. Chat ID {chat_id}. You may close this window."
            )
        except (OSError, ValueError):
            self.status.setText(
                "Telegram validation failed. Check the new token and internet connection."
            )
        finally:
            self.configure.setEnabled(True)


def discover_chat_id(token: str) -> str | None:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/getUpdates", method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise OSError("Telegram setup failed; credentials redacted") from error
    results = payload.get("result", []) if isinstance(payload, dict) else []
    for update in reversed(results):
        message = update.get("message", {}) if isinstance(update, dict) else {}
        chat = message.get("chat", {}) if isinstance(message, dict) else {}
        if isinstance(chat, dict) and "id" in chat:
            return str(chat["id"])
    return None


def save_user_environment(name: str, value: str) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def main() -> None:
    application = QApplication(sys.argv)
    window = TelegramSetup()
    window.show()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
