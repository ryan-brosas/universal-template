<!-- capsule-v2 -->
# Pagination — how do large collections ship without breaking clients later?

**Source:** Azure list + `nextLink`; Google AIP-158/132. **Question:** What must v1 of a list endpoint include?

## Pagination seam
**Azure response:**
```json
{"value":[{"id":"…","etag":"\"abc\""}],"nextLink":"https://service/.../items?api-version=2021-06-04&..."}
```

**Google request/response:** `page_size`, `page_token` → `next_page_token` (empty string/absent = end).

**Flow:** design pagination **before GA** (adding later is behaviorally breaking — AIP-158) → default page size when omitted → opaque continuation token/URL → last page **omits** `nextLink` (Azure: never `null`).
**Invariant:** page tokens/URLs must not grant authorization — auth re-checked each request (AIP-158).
**Invariant:** document that pages may skip/duplicate unless snapshot semantics promised (Azure).
**Probe:** list with >default items returns continuation; walk until no `nextLink`/`next_page_token`; changing `page_size` on continuation honored (Google).

## Verdict
Adopt day-one pagination with opaque cursors; adapt Azure absolute `nextLink` vs Google token fields; omit unpaginated list that returns unbounded arrays. Learning note: `api-design-learning-note.md`.
