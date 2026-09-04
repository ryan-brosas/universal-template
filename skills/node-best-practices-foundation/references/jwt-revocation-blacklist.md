<!-- capsule-v2 -->
# JWT revocation blacklist — statelessness is the vulnerability; the store must be shared

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** How do you revoke a token whose whole design says "never revoke"?

## External-store blacklist wired through isRevoked; jti as the key
**Path/Symbol:** `sections/security/expirejwt.md` (problem statement :3-6, config example :12-39).
**Signature:** `blacklist.configure({ tokenId: 'jti', strict: true, store: { type, host, port, keyPrefix, options } })` + `jwt({ secret, isRevoked: blacklist.isRevoked })`; logout calls `blacklist.revoke(req.user)`.
**Data Shape:** blacklist entries keyed by the JWT's `jti` claim; store = memcached/Redis (external), NOT in-process memory.

### Decisive source
```text
// expirejwt.md :10 — the invariant that kills naive deployments
it is important to not use the default store settings (in-memory) cache of
express-jwt-blacklist, but to use an external store such as Redis to revoke
tokens across many Node.js processes.
```

**Flow:** leaked/stolen token remains valid until expiry because verification is pure signature math (:5) → every protected route honors it → mitigation is a checked-at-verification blacklist: login/logout writes `jti`, `isRevoked` middleware consults it on EVERY request. `strict: true` fails toward rejection.
**Invariant:** THE PORTER'S TRAP: in-memory blacklists only cover ONE process — behind a cluster or PM2 workers, a revoked token still passes on sibling workers. Revocation necessarily sacrifices JWT's stateless property (Marc Busqué quote :43-44: "add a revocation layer ... even if it implies losing its stateless nature") — accept that cost explicitly.
**Probe:** no runner upstream. Deterministic probe: `grep -c '(in-memory)\|external store' sections/security/expirejwt.md` >= 2 && `grep -c "tokenId: 'jti'" sections/security/expirejwt.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "external store", "limit": 10}'
# resolves `sections/security/expirejwt.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt external-store + jti + strict as the revocation baseline. Adapt store choice to your infra (Redis/memcached). Pair with short expiries — the blacklist catches known-bad tokens, not unknown leaks.
