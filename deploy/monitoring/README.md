# Booth stats: Prometheus + Grafana

How the pieces fit:

```
K8s Smash --(HTTP /metrics, Prometheus text format)--> Prometheus (stores it) --> Grafana (draws the dashboard)
```

- **The game** publishes counters (matches, picks, wins, KOs, special moves, power-ups, FPS...). That text is the "metrics output".
  It is **off by default**: start the game with `--metrics-port 9877`.
- **Prometheus** scrapes that endpoint every few seconds and keeps the history.
- **Grafana** reads Prometheus and shows the dashboard.

## 1. Start the game with metrics on

```bash
.venv/bin/python -m k8ssmash --metrics-port 9877          # desktop
# on the Pi, add it to /etc/default/k8ssmash:  K8SSMASH_EXTRA_ARGS=--metrics-port 9877
curl localhost:9877/metrics                                # raw metrics; play a match and watch the numbers move
```

## 2. Start Prometheus + Grafana (needs Docker or Podman)

```bash
cd deploy/monitoring
docker compose up -d
```

Open **http://localhost:3000** (login `admin` / `admin`). The *K8s Smash: booth stats* dashboard is already there.
If the game runs on the Pi, edit `prometheus.yml` and set the target to `booth-pi.local:9877`.

## 3. Already have Prometheus and Grafana?

Add a scrape job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: k8ssmash
    static_configs:
      - targets: ["booth-pi.local:9877"]
```

and in Grafana choose *Dashboards, New, Import* and upload `deploy/grafana/k8ssmash-dashboard.json`, then pick your
Prometheus data source. Running them in Kubernetes works the same way (a `ServiceMonitor`/scrape config pointing at the Pi).

## What is measured

"Player stats" here means **per fighter**, not per person: how often each fighter is picked, wins, KOs, which specials
get used, which power-ups are grabbed, match counts and lengths, plus FPS, uptime and controllers connected. The game
does not track individual players. The endpoint has no authentication and listens on all interfaces, so use it on a
trusted network (or set `metrics_host` to `127.0.0.1` in the config).
