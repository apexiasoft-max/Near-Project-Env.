"""Windows Credential Manager boundary for local application secrets."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

TELEGRAM_TOKEN_TARGET = "NearProjectEnvironment/TelegramBotToken"


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    def read(self, target: str) -> str | None:
        if os.name != "nt":
            return None
        advapi32 = ctypes.WinDLL("Advapi32.dll")
        pointer = ctypes.POINTER(_Credential)()
        if not advapi32.CredReadW(target, 1, 0, ctypes.byref(pointer)):
            return None
        try:
            credential = pointer.contents
            blob = ctypes.string_at(
                credential.CredentialBlob, credential.CredentialBlobSize
            )
            return blob.decode("utf-16-le")
        finally:
            advapi32.CredFree(pointer)

    def write(self, target: str, secret: str) -> None:
        if os.name != "nt":
            raise OSError("Windows Credential Manager is unavailable")
        if not secret:
            raise ValueError("Secret cannot be empty")
        blob = secret.encode("utf-16-le")
        blob_buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        credential = _Credential()
        credential.Type = 1
        credential.TargetName = target
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(
            blob_buffer, ctypes.POINTER(ctypes.c_ubyte)
        )
        credential.Persist = 2
        credential.UserName = "NearProjectEnvironment"
        advapi32 = ctypes.WinDLL("Advapi32.dll")
        if not advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise OSError("Credential Manager rejected the secret")
