import json
import re
import urllib.request
from pathlib import Path

import pygame
import pytest

from k8ssmash.config import Config
from k8ssmash.main import App
from k8ssmash.metrics import DEFS, METRICS, PREFIX, Metrics, start_server
from k8ssmash.roster import roster
from k8ssmash.scenes.battle import READY_FRAMES, Battle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean():
    METRICS.reset()
    yield
    METRICS.reset()


def test_render_counters_labels_and_escaping():
    m = Metrics()
    m.inc("fighter_wins_total", fighter="Pod")
    m.inc("fighter_wins_total", 2, fighter="Pod")
    m.inc("specials_used_total", fighter='We"ird', move="a\\b")
    text = m.render()
    assert '# TYPE k8ssmash_fighter_wins_total counter' in text
    assert 'k8ssmash_fighter_wins_total{fighter="Pod"} 3' in text
    assert 'fighter="We\\"ird"' in text and 'move="a\\\\b"' in text
    assert "k8ssmash_uptime_seconds" in text and 'k8ssmash_info{version="0.1.0"} 1' in text


def test_summary_and_unknown_metric():
    m = Metrics()
    m.observe("match_duration_seconds", 30)
    m.observe("match_duration_seconds", 50)
    text = m.render()
    assert "# TYPE k8ssmash_match_duration_seconds summary" in text
    assert "k8ssmash_match_duration_seconds_sum 80" in text and "k8ssmash_match_duration_seconds_count 2" in text
    with pytest.raises(KeyError):
        m.inc("nope_total")


def test_exposition_format_is_valid_lines():
    m = Metrics()
    m.inc("items_picked_total", item="hpa")
    for line in m.render().strip().splitlines():
        assert line.startswith("#") or re.fullmatch(r'[a-z0-9_]+(\{[^}]*\})? [0-9.e+-]+', line), line


def test_broken_collector_does_not_break_scrape():
    m = Metrics()
    m.add_collector(lambda mm: 1 / 0)
    assert "k8ssmash_uptime_seconds" in m.render()


def test_http_endpoint_serves_metrics_and_health():
    m = Metrics()
    m.inc("matches_started_total", mode="versus")
    server = start_server(0, "127.0.0.1", m)
    assert server is not None
    port = server.server_address[1]
    try:
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3).read().decode()
        assert 'k8ssmash_matches_started_total{mode="versus"} 1' in body
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3).read() == b"ok\n"
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=3)
    finally:
        server.shutdown()


def test_port_in_use_is_not_fatal():
    first = start_server(0, "127.0.0.1", Metrics())
    try:
        assert start_server(first.server_address[1], "127.0.0.1", Metrics()) is None
    finally:
        first.shutdown()


@pytest.fixture
def app():
    a = App(Config())
    a.input.poll = lambda: None
    yield a
    pygame.quit()


def play_out(app, human, demo=False):
    b = Battle(app, roster()[:2], human=human, demo=demo, stocks=1)
    app.set_scene(b)
    b.frame = READY_FRAMES + 1
    b.fighters[1].x = -999
    b.fighters[1].last_hit_by = b.fighters[0]
    for _ in range(300):
        b.update()
        if b.winner is not None:
            break
    return b


def test_battle_reports_match_lifecycle(app):
    b = play_out(app, [True, True])
    assert b.winner == 0
    assert METRICS.get("matches_started_total", mode="versus") == 1
    assert METRICS.get("matches_finished_total", mode="versus") == 1
    assert METRICS.get("fighter_picks_total", fighter="Pod") == 1
    assert METRICS.get("fighter_wins_total", fighter="Pod") == 1
    assert METRICS.get("fighter_kos_total", fighter="Pod") == 1
    assert METRICS.get("match_duration_seconds_count") == 1
    b.update()
    assert METRICS.get("matches_finished_total", mode="versus") == 1  # reported once


def test_cpu_mode_label_and_demo_is_excluded(app):
    play_out(app, [True, False])
    assert METRICS.get("matches_started_total", mode="vs_cpu") == 1
    METRICS.reset()
    play_out(app, [False, False], demo=True)
    assert METRICS.render().count("matches_started") == 0 and METRICS.get("fighter_kos_total", fighter="Pod") == 0


def test_training_counts_separately(app):
    from k8ssmash.scenes.training import Training
    Training(app, roster()[:2])
    assert METRICS.get("matches_started_total", mode="training") == 1


def test_specials_and_items_are_counted(app):
    b = Battle(app, roster()[:2], human=[False, False], demo=False)
    app.set_scene(b)
    b.frame = READY_FRAMES + 1
    f = b.fighters[0]
    f.events.append("special")
    f._begin(f.stats.moves["special"])
    f.events.append("special")
    b.update()
    assert METRICS.get("specials_used_total", fighter="Pod", move="bubble") >= 1


def test_app_collector_exposes_fps_pads_and_scores(app):
    app.fps = 59.5
    app.scores.upsert("streak", "r", "AAA", 5, "Pod")
    text = METRICS.render()
    assert "k8ssmash_fps 59.5" in text and 'k8ssmash_high_score{board="streak"} 5' in text
    assert "k8ssmash_pads_connected" in text


def test_dashboard_only_queries_metrics_that_exist():
    dash = json.loads((ROOT / "deploy" / "grafana" / "k8ssmash-dashboard.json").read_text())
    assert dash["panels"] and dash["uid"]
    known = {PREFIX + n for n in DEFS} | {PREFIX + n + s for n, (k, _) in DEFS.items() if k == "summary"
                                          for s in ("_sum", "_count")}
    used = set()
    for panel in dash["panels"]:
        for t in panel["targets"]:
            used |= set(re.findall(r"k8ssmash_[a-z_]+", t["expr"]))
    assert used and used <= known, used - known


def test_monitoring_stack_files_are_consistent():
    import yaml
    mon = ROOT / "deploy" / "monitoring"
    compose = yaml.safe_load((mon / "docker-compose.yml").read_text())
    assert {"prometheus", "grafana"} <= set(compose["services"])
    prom = yaml.safe_load((mon / "prometheus.yml").read_text())
    job = prom["scrape_configs"][0]
    assert job["job_name"] == "k8ssmash" and job["static_configs"][0]["targets"][0].endswith(":9877")
    ds = yaml.safe_load((mon / "grafana/provisioning/datasources/prometheus.yml").read_text())["datasources"][0]
    assert ds["type"] == "prometheus" and ds["url"] == "http://prometheus:9090"
    # the provisioned copy of the dashboard is identical to the importable one and uses a datasource variable
    a = (ROOT / "deploy/grafana/k8ssmash-dashboard.json").read_text()
    b = (mon / "grafana/dashboards/k8ssmash-dashboard.json").read_text()
    assert a == b
    dash = json.loads(a)
    assert dash["templating"]["list"][0]["name"] == "DS_PROMETHEUS" and "__inputs" not in dash
