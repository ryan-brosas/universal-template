<!-- capsule-v2 -->
# Initial-credential single-use rotation — how do you consume a service-generated bootstrap secret exactly once, leaving no copy behind?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How is the generated `admin.password` converted into the operator secret without ever logging, persisting, or re-validating the intermediate credential?

## Read-once variable → raw-body PUT → credential dead
**Path/Symbol:** `entrypoint.sh:18-19`; contrast `:20` (second call already authenticates with the NEW password).
**Signature:** `initial=$(cat /nexus-data/admin.password)` then `curl -fsS -u "admin:$initial" -X PUT -H 'Content-Type: text/plain' --data-binary "$NEXUS_ADMIN_PASSWORD" .../security/users/admin/change-password >/dev/null`.
**Data Shape:** Intermediate secret exists ONLY in the shell variable and one curl argv. Request body = raw bytes of the new password (`text/plain` + `--data-binary` — NOT JSON). Response discarded (`>/dev/null`); failure surfaces via `-f` + `set -eu`.

### Decisive source
```sh
initial=$(cat /nexus-data/admin.password)
curl -fsS -u "admin:$initial" -X PUT -H 'Content-Type: text/plain' --data-binary "$NEXUS_ADMIN_PASSWORD" http://127.0.0.1:8081/service/rest/v1/security/users/admin/change-password >/dev/null
curl -fsS -u "admin:$NEXUS_ADMIN_PASSWORD" -X PUT -H 'Content-Type: application/json' --data '{"enabled":false,...}' http://127.0.0.1:8081/service/rest/v1/security/anonymous >/dev/null
```

**Flow:** read generated password once into memory → authenticate as `admin` USING THE GENERATED password → PUT the operator password as the raw request body → generated credential is permanently invalid from this moment → the very next API call (`:20`) authenticates with the NEW password, implicitly proving rotation succeeded before any further state changes (and before the marker is touched — ordering owned by `bootstrap-once-gate`).
**Invariant:** the intermediate credential is single-use and leaves no trace: never echoed, never written anywhere else, curl output silenced, and the leftover `admin.password` file is inert because the password it contains no longer authenticates. Two porter traps are pinned by the byte-exact excerpt: (1) the new password travels as a RAW TEXT BODY — wrapping it in JSON fails the endpoint; (2) `--data-binary` preserves bytes exactly, but like all curl `-d`/`--data-binary` forms it treats a LEADING `@` as a file reference — a secret beginning with `@` would abort the bootstrap (loud, fail-closed, but surprising; a porter hardening this should prepend-guard the variable). Basic-auth on the argv briefly exposes secrets in the process table — acceptable here because the call targets loopback only; do not carry this pattern to remote endpoints.
**Probe:** `tests/static.mjs` pins the endpoint literal (`assert.match(e,/change-password/)`; re-executed GREEN this pass). Mechanical pins: `grep -c 'Content-Type: text/plain' entrypoint.sh` ≥ 1, `grep -c -- --data-binary entrypoint.sh` ≥ 1, and the sequencing proof that `:20` authenticates with `$NEXUS_ADMIN_PASSWORD`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "change-password admin security users", limit: 10 });
```
(Config-shaped graph: no symbol for the shell call — retrieval confirms the env-var plane; the rotation sequence is whole-file-source-confirmed.)

## Verdict
Adopt the single-use ladder: read-once → auth-as-generated → raw-body overwrite → next-call-authenticates-with-new. Adapt endpoint/paths. Omit the loopback basic-auth shortcut when targeting remote APIs (use a secrets store or config file with 0600). Coverage caveat: behavior verified by reading; upstream ships no rotation integration test.
