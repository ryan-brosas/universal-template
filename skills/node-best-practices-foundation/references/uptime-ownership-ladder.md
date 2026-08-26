<!-- capsule-v2 -->
# Uptime-ownership ladder — who should restart a crashed Node process, and when does an extra manager HIDE failures?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How do you pick the right restart/uptime tool for a given hosting model, and why is a custom manager inside K8s counterproductive?

## Let the layer with the most placement data own restarts
**Path/Symbol:** `sections/production/guardprocess.md` (explainer :3-5, quotes :11-19) + `sections/docker/restart-and-replicate-processes.md` (explainer :3) + `sections/production/utilizecpu.md` (cluster :3, Node cluster quote :11).
**Signature:** decision ladder — bare metal → process manager (PM2) or systemd; containers/orchestrator (K8s/ECS) → let the orchestrator restart/replicate, invoke Node directly; CPU utilization → cluster module / PM2 / replicas.
**Data Shape:** the failure mode is stacking managers: "Running dozens of instances without a clear strategy and too many tools together (cluster management, docker, PM2) might lead to DevOps chaos" (guardprocess.md :3). Inside K8s, a custom PM2/cluster layer "will hide failures from the infrastructure" — the orchestrator can't relocate a container it thinks is healthy (README 5.5, restart-and-replicate :3).

### Decisive source
```text
// restart-and-replicate-processes.md :3 — orchestrator has the data
These local tools don't have the perspective and the data that is available
on the cluster level. For example, when the instances resources can host 3
containers and given 2 regions or zones, Kubernetes will take care to spread
the containers across zones ... When using local tools for restarting the
process the Docker orchestrator is not aware of the errors and can not make
thoughtful decisions like relocating the container to a new instance or zone.
```

**Flow:** choose the restart owner by who can make the best placement decision: bare metal → PM2/systemd; K8s/ECS → the orchestrator (invoke Node directly, no PM2/cluster inside). For CPU cores: bare metal → cluster module or PM2; K8s → replicas (orchestrator replicates, but won't verify cores are utilized — your duty, README 5.6).
**Invariant:** the restart layer must be the one with placement visibility. A nested manager that swallows crashes prevents the orchestrator from healing (relocation, zone spread). Node's own cluster doc warns distribution "tends to be very unbalanced" (utilizecpu :11) — a reason to prefer orchestrator-level replication.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'relocat\|placement\|zones' sections/docker/restart-and-replicate-processes.md` ≥ 2.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "placement", "limit": 10}'
# resolves `sections/docker/restart-and-replicate-processes.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the ownership ladder (infra-with-data owns restarts) for any deployment. Adapt the specific manager per host. Omit nothing — the hide-failures-from-orchestrator warning is the load-bearing lesson.
