"""Personality text for each fighter: what they say walking in, taunting, and winning."""
from __future__ import annotations

INTRO = {
    "Pod": "Scheduled!", "StatefulSet": "I'm not going anywhere.", "Kubectl": "kubectl get fight",
    "Chaos Monkey": "Ook ook!", "Sidecar": "Right beside you.", "Ingress": "Routing to victory.",
    "Operator": "Reconciling...", "OOMKiller": "Out of memory.",
}
TAUNT = {
    "Pod": "Ready, running!", "StatefulSet": "Persistent!", "Kubectl": "--force",
    "Chaos Monkey": "Chaos reigns!", "Sidecar": "Nice try.", "Ingress": "404 for you.",
    "Operator": "Desired state: win", "OOMKiller": "SIGKILL incoming",
}
WIN = {
    "Pod": "Scheduled, running, victorious!", "StatefulSet": "I remember every hit.",
    "Kubectl": "kubectl apply -f victory.yaml", "Chaos Monkey": "Ook! Chaos wins again!",
    "Sidecar": "Always right there when it counts.", "Ingress": "All traffic routed to victory.",
    "Operator": "State reconciled. You lose.", "OOMKiller": "Out of memory. Out of luck.",
}
