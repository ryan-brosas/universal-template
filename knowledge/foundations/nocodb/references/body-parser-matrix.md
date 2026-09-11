<!-- capsule-v2 -->
# Body-parser routing matrix — which content types hit express.json vs raw vs urlencoded, and where does the 50mb limit come from?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How are the three body middlewares scoped, and what breaks if you merge them?

## Type-scoped parser trio
**Path/Symbol:** `packages/nocodb/src/middlewares/json-body.middleware.ts` (whole 15L) · `raw-body.middleware.ts` (whole 12L) · `url-encode.middleware.ts` (whole 12L).
**Signature:** each wraps one express factory: `express.json({limit, type})`, `express.raw({type: '*/*'})`, `express.urlencoded({extended: true})`.
**Data Shape:** json limit = `process.env.NC_REQUEST_BODY_SIZE || '50mb'`; json type = `['application/json', 'application/scim+json']`.

### Decisive source
```ts
express.json({
  limit: process.env.NC_REQUEST_BODY_SIZE || '50mb',
  type: ['application/json', 'application/scim+json'],
})(req, res, next);
```
(json-body :12–:16; raw uses `type: '*/*'` for webhook signature verification paths needing the raw buffer)

**Flow:** route-level middleware registration decides which parser a route sees — SCIM gets its own content type folded into the JSON parser; raw-body routes (signature verification) must receive the UNparsed buffer or HMAC checks fail; urlencoded extended:true gives nested objects for legacy form posts. The env-var limit is read at REGISTRATION time (module init), not per-request.
**Invariant:** never stack json AFTER raw on the same route — the first parser consumes the stream; type-scoping is what makes coexistence safe. The 50mb default exists for import/base-restore payloads; lowering it globally breaks cross-instance migration uploads.
**Probe:** `cd packages/nocodb && grep -n "scim" src/middlewares/json-body.middleware.ts` (:12 single site) and `grep -n "NC_REQUEST_BODY_SIZE\|'50mb'" src/middlewares/json-body.middleware.ts` (:11 single limit site — ERRATUM pass 19 audit: shipped form carried a double-escaped `\|` alternation which matches nothing under single quotes, plus drifted :13/:14 cites; both re-derived against live source).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "JsonBodyMiddleware RawBodyMiddleware UrlEncodeMiddleware NC_REQUEST_BODY_SIZE scim", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt type-scoped parser selection and registration-time limit reads; adapt limits/content types; omit raw only if you verify no webhook-signature consumers exist.
