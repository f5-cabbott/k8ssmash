"""Minimal systemd notify client (sd_notify) so a hung game gets restarted. No-op outside systemd."""
from __future__ import annotations

import os
import socket
import time


class Watchdog:
    def __init__(self) -> None:
        addr = os.environ.get("NOTIFY_SOCKET", "")
        if addr.startswith("@"):
            addr = "\0" + addr[1:]
        self._addr = addr
        self._sock: socket.socket | None = None
        usec = int(os.environ.get("WATCHDOG_USEC", "0") or 0)
        self.interval = usec / 1_000_000 / 2 if usec else 0.0  # ping at half the timeout
        self._last = 0.0
        if self._addr:
            try:
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            except OSError:
                self._sock = None

    @property
    def active(self) -> bool:
        return self._sock is not None

    def notify(self, message: str) -> bool:
        if self._sock is None:
            return False
        try:
            self._sock.sendto(message.encode(), self._addr)
            return True
        except OSError:
            return False

    def ready(self) -> None:
        self.notify("READY=1")

    def ping(self, now: float | None = None) -> None:
        """Call every frame from the main loop; only talks to systemd when an interval has elapsed."""
        if not self.interval:
            return
        now = time.monotonic() if now is None else now
        if now - self._last >= self.interval:
            self._last = now
            self.notify("WATCHDOG=1")

    def stopping(self) -> None:
        self.notify("STOPPING=1")
