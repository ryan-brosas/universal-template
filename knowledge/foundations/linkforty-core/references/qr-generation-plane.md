<!-- capsule-v2 -->
# QR code generation plane — parameterized cache key, PNG-buffer vs SVG-text dual encoding, SHORTLINK_DOMAIN override

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How are rendered-image endpoints cached without serving the wrong format, and which URL gets encoded?

## GET /api/links/:id/qr
**Path/Symbol:** `src/routes/qr.ts:qrRoutes` (:8-144).
**Signature:** Query params `format='png'|'svg'`, `size` clamped 128-2048 (`Math.min(Math.max(parseInt(...),128),2048)`), `color='#000000'`, `bgcolor='#ffffff'`; cacheKey `` `qr:${id}:${format}:${size}:${color}:${bgcolor}` `` TTL 86400.
**Data Shape:** PNG cached as base64 STRING in Redis, decoded via `Buffer.from(cached,'base64')` on hit; SVG cached as text; both served with `Cache-Control: public, max-age=86400` + Content-Disposition inline filename from short_code.

### Decisive source
```ts
// qr.ts:79-82 — encoded URL choice:
const shortLinkDomain = process.env.SHORTLINK_DOMAIN || `${request.protocol}://${request.hostname}`;
const shortUrl = link.short_code ? `${shortLinkDomain}/${link.short_code}` : link.original_url;
// :87-93 — fixed render options:
{ errorCorrectionLevel: 'M', margin: 1, width: size, color: { dark: color, light: bgcolor } }
```

**Flow:** validate format enum → probe Redis cache (full param tuple in key so size/color variants never collide) → miss ⇒ load link (active-only) → encode short URL (env domain overrides request host for prod deployments behind different domains) → generate via qrcode lib → cache under same key → serve with long-lived browser caching; every Redis touch wrapped try/catch degrade-to-direct-generation.
**Invariant:** Cache key MUST include every render-affecting parameter (format especially — a png/svg collision serves corrupt images); QR encodes the SHORT link not the destination (scan-tracking depends on it); error-correction M + margin 1 are deliberate scannability choices.
**Probe:** `bash -c "grep -cF \"qr:\${id}\" src/routes/qr.ts"` → 1 (:36 — count lines, template literal spans one line); direct tests: none target qr.ts — recorded honest caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "qrcode png svg buffer cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt full-param cache keys + dual-encoding discipline for any image-render endpoint; adapt library/params; omit the env-domain override only if scans always occur on the serving host.
