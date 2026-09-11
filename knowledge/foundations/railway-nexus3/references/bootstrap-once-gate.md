<!-- capsule-v2 -->
# Bootstrap-once credential rotation — how does the entrypoint rotate the generated admin password exactly once across restarts?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How does a stateless platform container turn Nexus's generated bootstrap password into an operator-chosen secret without re-running the rotation on every restart?

## Marker-gated split entrypoint
**Path/Symbol:** `entrypoint.sh:6-8` (marker fast path), `entrypoint.sh:9-23` (bootstrap sequence).
**Signature:** `/bin/sh` script, `set -eu`; required env `NEXUS_ADMIN_PASSWORD` enforced by POSIX parameter expansion `${NEXUS_ADMIN_PASSWORD:?...}` at `:3`.
**Data Shape:** State lives entirely in the persistent volume: generated password file `/nexus-data/admin.password` (must be non-empty, `[ -s ]`), idempotency marker `/nexus-data/.railway-admin-configured`. Readiness probe `http://127.0.0.1:8081/service/rest/v1/status` polled 180 × 5 s (= 900 s budget).

### Decisive source
```sh
if [ -f /nexus-data/.railway-admin-configured ]; then
  exec su-exec nexus /opt/sonatype/nexus/bin/nexus run
fi
su-exec nexus /opt/sonatype/nexus/bin/nexus run &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null || true; wait "$pid"' TERM INT
ready=0
for i in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8081/service/rest/v1/status >/dev/null 2>&1 && [ -s /nexus-data/admin.password ]; then ready=1; break; fi
  sleep 5
done
[ "$ready" = 1 ] || { echo 'Nexus bootstrap timed out' >&2; exit 1; }
initial=$(cat /nexus-data/admin.password)
curl -fsS -u "admin:$initial" -X PUT -H 'Content-Type: text/plain' --data-binary "$NEXUS_ADMIN_PASSWORD" http://127.0.0.1:8081/service/rest/v1/security/users/admin/change-password >/dev/null
curl -fsS -u "admin:$NEXUS_ADMIN_PASSWORD" -X PUT -H 'Content-Type: application/json' --data '{"enabled":false,"userId":"anonymous","realmName":"NexusAuthorizingRealm"}' http://127.0.0.1:8081/service/rest/v1/security/anonymous >/dev/null
touch /nexus-data/.railway-admin-configured
chown 200:200 /nexus-data/.railway-admin-configured
wait "$pid"
```

**Flow:** require secret → prepare data dir (root) → marker exists ⇒ `exec` replace shell with server (no rotation, no trap needed) → else start server backgrounded under su-exec with TERM/INT trap forwarding → poll status **AND** password-file existence together (server up ≠ bootstrap material present) → fail loud `exit 1` on 900 s timeout → rotate password via `PUT /security/users/admin/change-password` authenticating with the *generated* password → disable anonymous access → write marker LAST → `wait` server in foreground forever.
**Invariant:** rotation runs strictly between "server first-boot complete" and "marker touched"; once the marker exists the entrypoint never calls the API again. Consequence a porter must not break: on restarts, the platform env var `NEXUS_ADMIN_PASSWORD` is NOT re-applied — authority over the real password transfers to the operator variable only at first boot. Also: marker is created AFTER both API mutations succeed (`set -eu` aborts otherwise), so a crash mid-bootstrap leaves no marker and the next boot retries safely.
**Probe:** `tests/static.mjs` (asserts `change-password` and `"enabled":false` literal JSON survive in `entrypoint.sh`). No runtime harness exists in-repo — record this caveat; deterministic probe is `grep -c change-password entrypoint.sh` ≥ 1 plus the marker filename grep.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "railway-admin-configured marker bootstrap", limit: 10 });
```
(Graph is config-shaped, not call-shaped: hits resolve `railway.deploy` Class + `__env__*` EnvVar nodes; the shell flow itself is confirmed by direct source read.)

## Verdict
Adopt the marker-gated once-only rotation pattern (works for any stateful service that generates first-boot credentials into a volume). Adapt paths/UID/port and the specific REST endpoints to the target product. Omit Railway-specific wiring. Direct-test caveat: template ships only static assertions; behavior verified by reading, not execution.
