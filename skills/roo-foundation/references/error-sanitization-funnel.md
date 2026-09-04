<!-- capsule-v2 -->
# Error sanitization + validation funnel — how do embedder failures become user-safe i18n messages?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** How are arbitrary provider errors mapped to status codes, connection classes, and redacted text?

## serialize-error → status ladder → connection-class ladder → passthrough
**Path/Symbol:** `src/services/code-index/shared/validation-helpers.ts` (:9-44 sanitize; :69-86 status map; :147-198 handleValidationError; :218-229 formatEmbeddingError).
**Signature:** `withValidationErrorHandling<T>(fn: () => Promise<T>, embedderType: string): Promise<{valid: boolean; error?: string}>`.
**Data Shape:** status extraction order: `error.status` → `error.response.status` → `/HTTP (\d+):/` in message → serialized fallbacks.

### Decisive source
```ts
// ports AFTER urls so ":6333" inside an already-redacted URL is not double-hit:
sanitized = sanitized.replace(/(?<!REDACTED_URL\]):(\d{2,5})\b/g, ":[REDACTED_PORT]")
// status ladder: 401/403 auth · 404 model-not-available(openai) vs invalid-endpoint(others) · 429 service-unavailable
```

**Flow:** sanitizeErrorMessage redacts URLs → emails → IPv4 → quoted paths → bare paths → standalone ports (negative lookbehind protects REDACTED_URL output). Validation maps statuses to i18n keys, then connection fingerprints (ENOTFOUND/ECONNREFUSED/ETIMEDOUT/AbortError/"HTTP 0:"/"No response") to connectionFailed, then JSON-parse failures, then passes the ORIGINAL message through if non-generic. Embedding-time errors get a 401-vs-status-vs-plain three-way format.
**Invariant:** redaction ORDER is load-bearing (URLs before paths before ports); 4xx→"configuration error" only for 400–599 — network-level zero-status errors must fall through to the connection ladder.
**Probe:** `src/services/code-index/shared/__tests__/validation-helpers.spec.ts`; behavioral probe EXECUTED verbatim (node eval of extracted function): `https://qdrant.internal:6333`, email, IPv4, quoted path, `:8080` all redacted in one pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "sanitizeErrorMessage withValidationErrorHandling extractStatusCode", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the ordered redaction pipeline and dual-ladder error classification wholesale. Adapt i18n keys. Omit serialize-error dependency if your host has structured errors.
