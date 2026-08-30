<!-- capsule-v2 -->
# Readiness conjunction poll — what does "ready to bootstrap" mean when HTTP-liveness and credential materialization are independent events?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** Why does the bootstrap loop require the status endpoint AND a non-empty password file together, instead of trusting either alone?

## Two-condition AND inside a bounded poll
**Path/Symbol:** `entrypoint.sh:12-17` (loop + timeout verdict); budget twin `railway.toml:6` (`healthcheckTimeout=900`).
**Signature:** `for i in $(seq 1 180); do if curl -fsS <status> && [ -s <password-file> ]; then ready=1; break; fi; sleep 5; done` — 180 iterations × 5 s = 900 s ceiling.
**Data Shape:** Condition A: HTTP 2xx from `http://127.0.0.1:8081/service/rest/v1/status` (`curl -fsS` fails loudly on HTTP errors; output discarded). Condition B: `[ -s /nexus-data/admin.password ]` — file EXISTS and size > 0. Output: `ready=1` latch or loud `{ echo ... >&2; exit 1; }`.

### Decisive source
```sh
ready=0
for i in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8081/service/rest/v1/status >/dev/null 2>&1 && [ -s /nexus-data/admin.password ]; then ready=1; break; fi
  sleep 5
done
[ "$ready" = 1 ] || { echo 'Nexus bootstrap timed out' >&2; exit 1; }
```

**Flow:** poll every 5 s → succeed ONLY when server answers AND the generated credential file is non-empty → break → rotate; otherwise burn all 180 attempts → print `Nexus bootstrap timed out` to stderr → `exit 1`.
**Invariant:** "server accepts HTTP" and "bootstrap credentials are readable" are independent events — Nexus writes `admin.password` late in first-boot, after the listener is up. Rotating on A alone yields a 401 (initial password unknown) or a race on the half-written file; gating on B alone can hang if the listener never binds. `[ -s ]` (non-empty) rather than `[ -e ]` rejects a created-but-zero-byte placeholder. The timeout does NOT retry in place: exiting 1 hands the retry to the platform's ON_FAILURE×10 policy, which restarts the container and re-enters the bootstrap with a FRESH 900 s window — an in-place retry loop would instead exhaust the platform healthcheck budget mid-bootstrap and get SIGKILLed into a corrupt-looking crash. The internal budget (900 s) equals `healthcheckTimeout` (900 s) by design: the platform must tolerate the ENTIRE bootstrap as "still starting".
**Probe:** `tests/static.mjs` pins the platform half (`assert.match(r,/service\\/rest\\/v1\\/status/)`, re-executed GREEN this pass). Mechanical pins for the internal half: `grep -c 'seq 1 180' entrypoint.sh` = 1, `grep -c '\[ -s /nexus-data/admin.password \]' entrypoint.sh` ≥ 1, and the cross-file arithmetic `180 * 5 == 900 == healthcheckTimeout` (grep both numbers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "railway deploy healthcheck", limit: 10 });
```
(Resolves `railway.deploy` over `railway.toml:4-9`; conjunction logic is shell-level, source-confirmed.)

## Verdict
Adopt the conjunction-poll contract for ANY service that materializes first-boot credentials asynchronously: poll liveness AND credential presence together, size-test the credential file, make the budget equal the platform's, and time out LOUD toward the platform's restart policy rather than retrying in place. Adapt endpoint, file path, and budgets (keep the equality). Omit product-specific status semantics.
