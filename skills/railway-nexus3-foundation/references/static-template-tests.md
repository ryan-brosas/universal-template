<!-- capsule-v2 -->
# Static template assertions — how do you regression-test a deployment TEMPLATE (no cluster required) so the security invariants can't silently rot?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** What does `npm test` actually verify, and which template properties are pinned by it?

## Six-assertion file-shape test
**Path/Symbol:** `tests/static.mjs:1` (single-line ESM module; `npm test` wired via `package.json` `{"scripts":{"test":"node tests/static.mjs"}}`).
**Signature:** reads four files as text — `Dockerfile`, `entrypoint.sh`, `railway.toml`, `scripts/smoke.py` — then six `assert.match`/`doesNotMatch` regex pins.
**Data Shape:** pure text assertions, zero network, zero Docker. Pins: (1) image digest-pin format `/nexus3:3\.95\.2-alpine@sha256:[a-f0-9]{64}/`, (2) absence of any `:latest` tag, (3) `change-password` literal present in entrypoint, (4) `"enabled":false` literal present (anonymous-disable payload), (5) `/service\/rest\/v1\/status/` present in railway.toml (healthcheck), (6) `ACCEPT_NEXUS_EULA` present in smoke.py (consent gate).

### Decisive source
```js
assert.match(d,/nexus3:3\.95\.2-alpine@sha256:[a-f0-9]{64}/);assert.doesNotMatch(d,/:latest/);
assert.match(e,/change-password/);assert.match(e,/"enabled":false/);
assert.match(r,/service\/rest\/v1\/status/);
assert.match(s,/ACCEPT_NEXUS_EULA/);
```

**Flow:** upgrade guard-rail: anyone bumping the base image, editing the entrypoint, or touching deploy config must keep these six literals intact or CI (`npm test`) fails.
**Invariant:** the SECURITY-critical surface of a template is exactly its load-bearing literals — pin those, not the whole file. Digest-pinning + no-latest prevents supply-chain drift; change-password + enabled:false prevent bootstrap-regression; healthcheck path + EULA env prevent config rot.
**Probe:** the test IS the probe: `node tests/static.mjs` → prints "static template checks passed" (exit 0). Executed below in the behavior-pressure-test record.

## Get live surrounding code
**Retrieve:** BM25 search_graph cannot see the console literal (verified live this pass); use line-exact search_code:
```
codebase-memory-mcp search_code {"project":"railway-template-nexus3","pattern":"static template checks passed","limit":5}
```
→ EXECUTED this pass: Variable `tests.static.d` in tests/static.mjs lines 1-1, match at `"1"` (the whole-suite line).

## Verdict
Adopt the static-literal test pattern for ANY infra-as-template repo (Terraform modules, compose files, platform templates): assert the dangerous-to-lose literals, run in plain node with zero services. Adapt the assertion set to the template's own security surface. Omit nothing behavioral.

> ERRATUM pass 5 (deepening-B lane): the two `3\.95\.1` literals above previously carried the pass-1 pin version; re-derived against live source at 18e177a6 — the test asserts `3\.95\.2`. Excerpt now byte-matches the pin.
