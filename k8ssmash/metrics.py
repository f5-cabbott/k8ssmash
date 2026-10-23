"""Optional Prometheus metrics. Counters are always collected (they're just dict increments);
the HTTP endpoint only exists when started with --metrics-port."""
from __future__ import annotations

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

log = logging.getLogger("k8ssmash.metrics")

PREFIX = "k8ssmash_"
# name -> (type, help). Summary metrics expose _sum and _count.
DEFS: dict[str, tuple[str, str]] = {
    "matches_started_total": ("counter", "Matches started, by mode (versus, vs_cpu, training)."),
    "matches_finished_total": ("counter", "Matches that reached a result, by mode."),
    "match_duration_seconds": ("summary", "Length of finished matches in seconds."),
    "fighter_picks_total": ("counter", "Times each fighter was picked."),
    "fighter_wins_total": ("counter", "Matches won by each fighter."),
    "fighter_kos_total": ("counter", "Knock-outs scored by each fighter."),
    "specials_used_total": ("counter", "Special moves used, by fighter and move."),
    "items_picked_total": ("counter", "Power-ups picked up, by item."),
    "high_score": ("gauge", "Best value on each leaderboard."),
    "pads_connected": ("gauge", "Controllers currently assigned to a player."),
    "fps": ("gauge", "Rendered frames per second."),
    "uptime_seconds": ("gauge", "Seconds since the game started."),
    "info": ("gauge", "Build information (always 1)."),
}


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _labels(items: tuple[tuple[str, str], ...]) -> str:
    return "{" + ",".join(f'{k}="{_esc(v)}"' for k, v in items) + "}" if items else ""


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, dict[tuple[tuple[str, str], ...], float]] = {}
        self._collectors: list[Callable[["Metrics"], None]] = []
        self.started = time.monotonic()
        self.version = "0.1.0"

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        if name not in DEFS:
            raise KeyError(f"unknown metric {name!r}")
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            series = self._values.setdefault(name, {})
            series[key] = series.get(key, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        if name not in DEFS:
            raise KeyError(f"unknown metric {name!r}")
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            self._values.setdefault(name, {})[key] = float(value)

    def observe(self, name: str, value: float, **labels: str) -> None:
        """Summary observation: adds to <name>_sum and increments <name>_count."""
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            for suffix, amount in (("_sum", value), ("_count", 1.0)):
                series = self._values.setdefault(name + suffix, {})
                series[key] = series.get(key, 0.0) + amount

    def get(self, name: str, **labels: str) -> float:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            return self._values.get(name, {}).get(key, 0.0)

    def add_collector(self, fn: Callable[["Metrics"], None]) -> None:
        """Collectors refresh gauges (fps, pads, uptime) right before a scrape."""
        self._collectors.append(fn)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()

    def render(self) -> str:
        self.set("uptime_seconds", time.monotonic() - self.started)
        self.set("info", 1, version=self.version)
        for fn in self._collectors:
            try:
                fn(self)
            except Exception:  # a broken collector must never break the scrape
                log.exception("metrics collector failed")
        lines: list[str] = []
        with self._lock:
            for name, (kind, help_text) in DEFS.items():
                full = PREFIX + name
                names = [name + "_sum", name + "_count"] if kind == "summary" else [name]
                if not any(self._values.get(n) for n in names):
                    continue
                lines += [f"# HELP {full} {help_text}", f"# TYPE {full} {kind}"]
                for n in names:
                    for key, value in sorted(self._values.get(n, {}).items()):
                        lines.append(f"{PREFIX}{n}{_labels(key)} {value:g}")
        return "\n".join(lines) + "\n"


METRICS = Metrics()


class _Handler(BaseHTTPRequestHandler):
    metrics = METRICS

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path.split("?")[0] == "/metrics":
            body, ctype, code = self.metrics.render().encode(), "text/plain; version=0.0.4; charset=utf-8", 200
        elif self.path == "/healthz":
            body, ctype, code = b"ok\n", "text/plain", 200
        else:
            body, ctype, code = b"not found\n", "text/plain", 404
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # keep scrapes out of the journal
        pass


def start_server(port: int, host: str = "0.0.0.0", metrics: Metrics | None = None) -> ThreadingHTTPServer | None:
    handler = type("Handler", (_Handler,), {"metrics": metrics or METRICS})
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        log.warning("metrics endpoint disabled: cannot bind %s:%s (%s)", host, port, exc)
        return None
    threading.Thread(target=server.serve_forever, name="metrics", daemon=True).start()
    log.info("metrics on http://%s:%s/metrics", host, server.server_address[1])
    return server
