<!-- capsule-v2 -->
# Platform healthcheck + restart contract — how do the railway.toml deploy knobs and the entrypoint's readiness loop combine into one coherent liveness budget?

**Source:** railway-template-nexus3 EPL-1.0 `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58`; Codebase Memory `railway-template-nexus3`. **Question:** How are platform-level health/restart settings tuned for a slow-booting JVM service, and why those numbers?

## 900-second patience pair
**Path/Symbol:** `railway.toml:1-9` (`[build]` + `[deploy]` tables; graph nodes `railway.build`/`railway.deploy`, lines 1-4 / 4-9), paired with `entrypoint.sh:13-17`.
**Signature:** TOML: `[build] builder="DOCKERFILE" dockerfilePath="Dockerfile"`; `[deploy] healthcheckPath="/service/rest/v1/status" healthcheckTimeout=900 restartPolicyType="ON_FAILURE" restartPolicyMaxRetries=10`.
**Data Shape:** healthcheckPath is an app-relative path hitting Nexus's own status endpoint (same URL the entrypoint polls locally at :14). healthcheckTimeout 900 s == entrypoint budget 180 × 5 s = 900 s. Restart on failure, capped at 10 retries.

### Decisive source
```toml
[build]
builder="DOCKERFILE"
dockerfilePath="Dockerfile"
[deploy]
healthcheckPath="/service/rest/v1/status"
healthcheckTimeout=900
restartPolicyType="ON_FAILURE"
restartPolicyMaxRetries=10
```

**Flow:** platform builds from the pinned Dockerfile → waits up to 15 min for `/service/rest/v1/status` to pass → meanwhile the in-container entrypoint runs its OWN identical-status poll (loopback, not exposed) before performing bootstrap mutations → on crash, ON_FAILURE restarts up to 10 times.
**Invariant:** the two budgets must stay coherent: the platform must be willing to wait AT LEAST as long as first boot takes (JVM heap init + first-run DB migration easily exceed a default 60-300 s probe timeout, which would kill-loop a healthy bootstrap). The entrypoint's internal poll exists so credential rotation happens exactly once and never races the platform's external probe. README (:6) adds the sizing half of the contract: ≥2 GB RAM, ONE replica, never scale horizontally — embedded-OrientDB storage cannot be multi-writer.
**Probe:** `tests/static.mjs` asserts the status path literal appears in `railway.toml`. Deterministic probe: `grep -c 'healthcheckTimeout=900' railway.toml` = 1. Runtime caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "railway-template-nexus3", query: "railway deploy healthcheckPath restartPolicy", limit: 10 });
```

## Verdict
Adopt the matched-budgets pattern (platform probe window == in-container bootstrap window) plus ON_FAILURE-with-cap for any slow-boot stateful template. Adapt numbers to the target JVM/app's measured cold-start. Omit Railway-specific key names when porting to another platform; keep the equality-of-budgets invariant.
