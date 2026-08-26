<!-- capsule-v2 -->
# Request throttling + payload caps — two different DoS doors, two different knobs

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** How do you keep request floods and giant bodies from taking the single-threaded app down?

## Rate limit per client (points/duration/block) AND cap body bytes at the edge
**Path/Symbol:** `sections/security/limitrequests.md` (raw-node limiter :9-37, express middleware :45-57) + `sections/security/requestpayloadsizelimit.md` (express :15-34, nginx :40-58).
**Signature:** `new RateLimiterRedis({ storeClient, points: 20, duration: 1, blockDuration: 2 })`; `express.json({ limit: '300kb' })`; nginx `client_max_body_size 1m;`.
**Data Shape:** limiter keyed by `req.socket.remoteAddress`; over-consumption throws → mapped to HTTP 429. Body-parser default is 100kb — the doc RAISES it to 300kb explicitly, never removes it.

### Decisive source
```javascript
// limitrequests.md :17-22 + :26-33
const rateLimiter = new RateLimiterRedis({
  storeClient: redisClient,
  points: 20, duration: 1,
  blockDuration: 2, // block for 2 seconds if consumed more than 20 points/s
});
const rateLimiterRes = await rateLimiter.consume(req.socket.remoteAddress);
} catch { res.writeHead(429); res.end('Too Many Requests'); }

// requestpayloadsizelimit.md :20
app.use(express.json({ limit: '300kb' })); // body-parser defaults to 100kb
```

**Flow:** flood door: N concurrent requests each cost CPU on the ONE event loop → per-client consume() either admits or 429s before handler work. Size door: parsing huge JSON bodies is "a performance-heavy operation" (:5) → byte cap rejects early (413) before parse. Behind a proxy: `app.enable('trust proxy')` so req.ip is the real client (:47-48); nginx can carry the same caps at L7 (`http{}`/`server{}`/`location` scopes all support `client_max_body_size`).
**Invariant:** rate limiting ≠ login brute-force protection (`two-tier-brute-force-limiter` owns that): this contract protects THROUGHPUT for everyone, not credential guessing. Content-type checking stays your job even with body-parser ("body-parser does not check for content types", :25-28 → 415 on mismatch).
**Probe:** no runner upstream. Deterministic probe: `grep -c 'client_max_body_size' sections/security/requestpayloadsizelimit.md` >= 3 && `grep -c "limit: '300kb'" sections/security/requestpayloadsizelimit.md` >= 1.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "concurrent", "limit": 10}'
# resolves `sections/security/limitrequests.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt both knobs as standard middleware/edge config. Adapt thresholds to endpoint cost (upload routes get larger caps in scoped location blocks). Omit raw-http form if Express already wraps it.
