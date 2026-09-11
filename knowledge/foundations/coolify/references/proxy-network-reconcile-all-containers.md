<!-- capsule-v2 -->
# Proxy network reconciliation scans ALL managed containers, not just running

## Source
Coolify `main@98116397`, `bootstrap/helpers/proxy.php` (`connectProxyToNetworks`, :108-135, one-token change :123). Drift-introduced fix (upstream commit `16352fad`); direct test `tests/Feature/Proxy/RuntimeNetworkReconciliationTest.php` (renamed assertion: "discovers managed container networks regardless of container status").

## Question
Why must the proxy's reconnect loop enumerate stopped/exited containers too — and why is that safe here when a similar `-a` flag elsewhere would be wrong?

## Path / Symbol
`connectProxyToNetworks(Server $server): Collection` — non-swarm branch returns a shell for-loop string list.

## Signature
```php
'for network in $(docker inspect $(docker ps -a --filter label=coolify.managed=true --format "{{.ID}}") --format=\'{{range $network, $_ := .NetworkSettings.Networks}}{{println $network}}{{end}}\' 2>/dev/null | sort -u); do'
//                                                                 ^^^ was: docker ps (running only)
```

## Data Shape
Pipeline: managed container IDs → each container's NetworkSettings.Networks names → dedupe via `sort -u` → per-network guard chain (`bridge/host/none/default` skipped; `docker network inspect` existence check) → `docker network connect ... || true`.

## Decisive source
The pre-fix loop discovered only RUNNING containers' networks. After a host reboot the proxy container starts BEFORE the app containers it fronts; every managed-but-stopped container's target network was invisible at reconcile time, so the proxy came up detached from networks that its (not-yet-started) services use. The fix widens discovery to all containers carrying `coolify.managed=true` — a container's NetworkSettings persist across stops, so exited members still contribute their networks.

## Flow / Invariant
INVARIANTS:
1. Discovery predicate = LABEL (`coolify.managed=true`), never runtime status.
2. Safety of `-a` here comes from three downstream guards: skip built-in networks by name, require the network to EXIST on this host before connecting, and `|| true` so already-connected/absent targets never fail the loop.
3. `sort -u` makes the loop idempotent — N containers sharing one network yield ONE connect attempt.
4. Swarm branch stays separate (overlay driver + `--attachable` create-if-missing) and is NOT touched by this widening.

## Probe (direct tests)
From repo root:
```bash
grep -c 'docker ps -a --filter label=coolify.managed=true' bootstrap/helpers/proxy.php
grep -c "toContain('docker ps -a --filter label=coolify.managed=true')" tests/Feature/Proxy/RuntimeNetworkReconciliationTest.php
grep -c 'docker network connect "$network" coolify-proxy >/dev/null 2>&1 || true' bootstrap/helpers/proxy.php
```
Expect 1 / 1 / 1. (PHPUnit runner blocked honestly.)

## Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-coolify","query":"connectProxyToNetworks","limit":3}'
```
→ rank-1 `Function bootstrap/helpers/proxy.php 108-135`.

## Verdict
ADOPT the reconciliation contract verbatim (label-scoped status-independent discovery + existence-guarded idempotent connects); adapt the shell to your orchestrator's API.
