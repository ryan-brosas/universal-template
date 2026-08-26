<!-- capsule-v2 -->
# Anonymous-access disable — what exact API call and payload turns off Nexus's anonymous realm, and why is the order after password rotation load-bearing?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** What single request hardens a fresh Nexus against unauthenticated read access, and when must it fire?

## Disable-anonymous PUT
**Path/Symbol:** `entrypoint.sh:20` (the request), `scripts/smoke.py:4` (negative probe).
**Signature:** `PUT /service/rest/v1/security/anonymous` with JSON body `{"enabled":false,"userId":"anonymous","realmName":"NexusAuthorizingRealm"}`; auth `admin:$NEXUS_ADMIN_PASSWORD` (the NEW password — this is also its first proof-of-life check).
**Data Shape:** Full-state toggle: the body carries all three fields (`enabled`, `userId`, `realmName`) even though only `enabled` changes. `-fsS` curl flags make any non-2xx or transport error abort the script under `set -eu` — silent partial bootstrap is impossible.

### Decisive source
```sh
curl -fsS -u "admin:$NEXUS_ADMIN_PASSWORD" -X PUT -H 'Content-Type: application/json' --data '{"enabled":false,"userId":"anonymous","realmName":"NexusAuthorizingRealm"}' http://127.0.0.1:8081/service/rest/v1/security/anonymous >/dev/null
```

**Flow:** rotate admin password first (:19) → then disable anonymous (:20) → only then touch marker (:21). Order is load-bearing: disabling anonymous BEFORE rotating would still leave the rotation authenticated with the throwaway generated secret in `admin.password`; rotating first means every subsequent mutation (and every operator login) uses the operator-chosen secret, so a leaked generated file no longer grants anything.
**Invariant:** after successful bootstrap, unauthenticated requests to protected endpoints must fail with 401/403 — never 200. The template treats anonymous-off as part of bootstrap, not an optional hardening step.
**Probe:** `tests/static.mjs` asserts `"enabled":false` appears verbatim in `entrypoint.sh`. Runtime twin: `scripts/smoke.py:4` asserts `GET /security/users` without auth returns 401/403 on the live deployment.

## Get live surrounding code
**Retrieve:** BM25 search_graph returns total:0 for the payload tokens (shell literals are invisible to it on this config-shaped graph — verified live this pass); use line-exact search_code:
```
codebase-memory-mcp search_code {"project":"railway-template-nexus3","pattern":"NexusAuthorizingRealm","limit":5}
```
→ EXECUTED this pass: Module `entrypoint` lines 1-24, match at `"20"` (the exact cited request line).

## Verdict
Adopt the full-body state-toggle + fail-loud curl idiom for any product exposing a similar security-realm REST toggle. Adapt endpoint path/realm name per product version. Omit nothing behavioral; note the smoke test's 401-or-403 tolerance (both codes are legitimate depending on whether the endpoint exists for anonymous callers).
