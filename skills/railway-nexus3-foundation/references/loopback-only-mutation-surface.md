<!-- capsule-v2 -->
# Loopback-only mutation surface — why do ALL privileged API calls target 127.0.0.1 while the platform probe and smoke tests hit the public URL?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** Which network surface performs privileged mutations, and why is that split load-bearing for a container whose admin secret transits the process table?

## Three surfaces, three trust levels
**Path/Symbol:** `entrypoint.sh:14,19,20` (all three curls → `http://127.0.0.1:8081/...`), `railway.toml:5` (`healthcheckPath="/service/rest/v1/status"` — platform probes over public HTTPS), `scripts/smoke.py:3` (`b=os.environ['BASE_URL']` — external verifier), `Dockerfile:6` (`EXPOSE 8081`).
**Signature:** in-container mutations authenticate with `admin:$initial` / `admin:$NEXUS_ADMIN_PASSWORD` via curl `-u` basic-auth on the ARGV against loopback; nothing privileged is ever issued toward `$BASE_URL` or any non-loopback host.

### Decisive source
```sh
curl -fsS http://127.0.0.1:8081/service/rest/v1/status >/dev/null 2>&1 && ...
curl -fsS -u "admin:$initial" ... http://127.0.0.1:8081/service/rest/v1/security/users/admin/change-password >/dev/null
curl -fsS -u "admin:$NEXUS_ADMIN_PASSWORD" ... http://127.0.0.1:8081/service/rest/v1/security/anonymous >/dev/null
```

**Flow:** the entrypoint polls, rotates, and hardens strictly over loopback; the platform healthchecks and the operator's smoke script exercise only unauthenticated status plus credentialed READS/writes through the product's own auth over TLS-terminated public HTTPS.
**Invariant:** privileged credential-bearing traffic never leaves the container network namespace. This is what makes two otherwise-questionable choices safe: (1) `initial-credential-single-use` documents basic-auth-on-argv leaking secrets to the process table — acceptable ONLY because the call targets loopback where eavesdropping requires already being inside the container; (2) the generated `admin.password` remains valid for the entire bootstrap window — harmless while reachable solely from inside, catastrophic if the rotation endpoint were called over an interface an attacker could reach. A porter who points the rotation at `$BASE_URL` "to test it like the smoke script does" re-exposes both hazards over the public internet. The flip side the same file teaches: the PUBLIC surface must expose no privileged capability without auth — which `smoke-crud-roundtrip`'s negative assertions (`/security/users` anon → 401/403; wrong password → 401/403) verify from OUTSIDE.
**Probe:** mechanical pins EXECUTED this pass at pin: `grep -c '127\.0\.0\.1' entrypoint.sh` = 3 (every curl), `grep -cF 'curl -fsS' entrypoint.sh` = 3, and the negative form `grep -cF '$BASE_URL' entrypoint.sh` = 0 — BASE_URL exists only in `scripts/smoke.py` (`grep -cF 'BASE_URL' scripts/smoke.py` = 1). Static twin green: `node tests/static.mjs` rc=0.

## Get live surrounding code
**Retrieve:** BM25 search_graph cannot see shell literals on this config-shaped graph (live-verified total:0 for loopback queries); use line-exact search_code:
```
codebase-memory-mcp cli search_code '{"project":"railway-template-nexus3","pattern":"127.0.0.1","limit":4}'
```
→ Module `entrypoint` lines 1-24, matches at 14;19;20 (verified this pass).

## Verdict
Adopt the surface split: privileged/bootstrap traffic loopback-only; public surface limited to health + authenticated product APIs verified by negative external probes. Adapt port/interface per product. Omit when your runtime has no shared network namespace threat model — but then document WHY, as this template does implicitly.
