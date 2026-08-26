<!-- capsule-v2 -->
# Schema-validation gate — declare what's acceptable, fail fast at middleware, 400 on deviation

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Where in the request path does input validation belong, and what shape does the rule take?

## JSON-schema (or joi) declared per entity, enforced by router middleware BEFORE handlers
**Path/Symbol:** `sections/security/validation.md` (:3 explainer, schema example :9-27, class validator :33-48, middleware wiring :53-58).
**Signature:** `router.post('/', validator(Product.validate), handler)` — validation as composable route middleware returning 400 on failure.
**Data Shape:** draft-06 JSON-schema: typed `properties`, constraints (`exclusiveMinimum: 0`), `required` array; joi as the fluent-syntax alternative.

### Decisive source
```text
// validation.md :3 — the doctrine
Validation is about being very explicit on what payload our app is willing
to accept and failing fast should the input deviate from the expectations.
...
ensure to run the validation as early as possible - For example, by using
Express middleware that validates the request body before the request is
passed to the route handler
// :55 — the wiring
router.post('/' , validator(Product.validate), async (req, res, next) => {
```

**Flow:** undeclared payloads let attackers probe structure/value/length (:3) → DoS via unexpected shapes + deserialization surprises → schema declares the accept-set ONCE and shares it with frontend consumers; middleware enforces before any handler logic runs; failures die as 400s.
**Invariant:** position is load-bearing — validation AFTER handler entry is already too late (the doc says "as early as possible"). Schemas can't cover every rule ("JSON syntax can't cover all validation scenario", :5) so a custom-code escape hatch exists — but the DEFAULT must be declarative. This capsule is the upstream feeder for `injection-proof-data-access`: validated payloads are what parameterized queries safely bind.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'exclusiveMinimum\|validator(Product.validate)' sections/security/validation.md` >= 2.
**Retrieve:** **Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "exclusiveMinimum", "limit": 10}'
# resolves `sections/security/validation.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt schema-first validation with middleware enforcement as the API contract. Adapt library choice (jsonschema/joi/TypeScript-class hybrids). Omit client-side-only validation — server-side is the security boundary.
