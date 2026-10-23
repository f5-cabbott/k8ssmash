import socket
import time

import pytest

from k8ssmash.config import Config
from k8ssmash.main import EXIT_COMBO, EXIT_FRAMES, App, apply_args, parse_args
from k8ssmash.scenes.title import Title
from k8ssmash.watchdog import Watchdog


def test_booth_mode_locks_down():
    cfg = apply_args(Config(), parse_args(["--booth"]))
    assert cfg.fullscreen and not cfg.dev_keys


def test_cli_flags():
    cfg = apply_args(Config(), parse_args(["--windowed", "--size", "2560x1440", "--no-items", "--mute"]))
    assert (cfg.width, cfg.height, cfg.items, cfg.muted, cfg.fullscreen) == (2560, 1440, False, True, False)


def test_booth_env(monkeypatch):
    monkeypatch.setenv("K8SSMASH_BOOTH", "1")
    assert not apply_args(Config(), parse_args([])).dev_keys


def test_exit_combo_quits_only_after_hold():
    app = App(Config())
    app.input.poll = lambda: None
    app.set_scene(Title(app))
    for _ in range(EXIT_FRAMES - 5):
        app.input.players[0].update(set(EXIT_COMBO))
        app.step()
    assert app.running
    for _ in range(10):
        app.input.players[0].update(set(EXIT_COMBO))
        app.step()
    assert not app.running


def test_exit_combo_released_resets():
    app = App(Config())
    app.input.poll = lambda: None
    app.set_scene(Title(app))
    for _ in range(EXIT_FRAMES - 5):
        app.input.players[0].update(set(EXIT_COMBO))
        app.step()
    app.input.players[0].update(set())
    app.step()
    for _ in range(EXIT_FRAMES - 5):
        app.input.players[0].update(set(EXIT_COMBO))
        app.step()
    assert app.running


def test_watchdog_is_noop_without_systemd(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    wd = Watchdog()
    assert not wd.active and not wd.notify("READY=1")
    wd.ping()  # must not raise


def test_watchdog_talks_to_notify_socket(monkeypatch, tmp_path):
    path = str(tmp_path / "notify.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(path)
    server.settimeout(1)
    monkeypatch.setenv("NOTIFY_SOCKET", path)
    monkeypatch.setenv("WATCHDOG_USEC", "4000000")  # 4s timeout -> ping every 2s
    wd = Watchdog()
    assert wd.active and wd.interval == 2.0
    wd.ready()
    assert server.recv(64) == b"READY=1"
    wd.ping(now=time.monotonic() + 10)
    assert server.recv(64) == b"WATCHDOG=1"
    wd.ping(now=time.monotonic() + 10.5)  # inside the interval: stays quiet
    server.settimeout(0.1)
    with pytest.raises(socket.timeout):
        server.recv(64)
