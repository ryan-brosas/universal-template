<!-- capsule-v2 -->
# Trusted origin gate — loopback default plus exact remote-origin sidecar

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should auth/settings HTTP routes trust local callers by default while requiring an exact persisted origin for remote callers and failing closed on browser metadata or sidecar errors?

## trustedRequestDecision
**Path/Symbol:** `src/auth-routes.ts:256-298 loopbackHost/exactOrigin/effectiveOrigin/sameOriginMetadata` and `src/auth-routes.ts:309-336 trustedRequestDecision`.
**Signature:** `trustedRequestDecision(req: IncomingMessage, trustedOrigins?: OpenAICodexTrustedOriginsStore): Promise<TrustedRequestDecision>`; decision is `{ trusted: true }` or `{ trusted: false; error: 'forbidden' | 'remote-web-origin-not-trusted' }`.
**Data Shape:** Trust is derived from peer address, `Host`, normalized effective scheme/origin, optional `Origin`, `sec-fetch-site`, and a persistent exact-origin allowlist. Loopback peer + loopback host is the local fast path; non-loopback callers must be present in the sidecar.

### Decisive source
```ts
const crossSite = typeof fetchSite === 'string'
  ? fetchSite.trim().toLowerCase() === 'cross-site'
  : Array.isArray(fetchSite) && fetchSite.some(value => value.trim().toLowerCase() === 'cross-site')
if (crossSite) return { trusted: false, error: 'forbidden' }
const host = req.headers.host
if (typeof host !== 'string') return { trusted: false, error: 'forbidden' }
const origin = effectiveOrigin(req, host)
if (origin === undefined) return { trusted: false, error: 'forbidden' }
if (!sameOriginMetadata(req, host)) return { trusted: false, error: 'forbidden' }
if (localPeer && loopbackHost(host)) return { trusted: true }
try {
  if (await trustedOrigins.has(origin)) return { trusted: true }
} catch {
  return { trusted: false, error: 'forbidden' }
}
return { trusted: false, error: REMOTE_WEB_ORIGIN_NOT_TRUSTED }
```

**Flow:** reject cross-site metadata, missing/invalid host, invalid scheme/origin, and mismatched `Origin`; accept only loopback host from a loopback peer; otherwise query the current trusted-origin sidecar; map malformed sidecar reads to generic forbidden and absent remote entries to the stable trust-required error.
**Invariant:** an attacker-controlled Host/Origin pair cannot become trusted merely by agreeing with itself; remote trust is exact-origin and live-read; malformed or too-broad sidecar state fails closed without exposing contents; the route authorizer checks this decision before auth or settings side effects.
**Probe:** `tests/auth-routes.spec.ts:174-270` (remote origin becomes trusted only after exact sidecar trust, mismatched port/cross-site/DNS-rebinding are rejected, loopback cases are accepted), plus `tests/auth-routes.spec.ts:204-226` (status/login/logout routes return the stable 403 before mocked auth calls). The file is parse-partial only at line 40, which was directly read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth-routes\\.trustedRequestDecision', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the ordered fail-closed trust ladder and exact-origin sidecar lookup. Adapt loopback address policy, normalization store, and error vocabulary; retain the rule that request metadata and peer identity are independent checks. Omit permissive host-based or cross-site bypasses. Coverage: `src/auth-routes.ts` and `src/auth-paths.ts` are `no_recorded_issue` + `metadata_match`; `tests/auth-routes.spec.ts` is partial at line 40 only.
