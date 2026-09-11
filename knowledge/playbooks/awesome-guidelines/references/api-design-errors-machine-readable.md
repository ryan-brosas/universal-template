<!-- capsule-v2 -->
# Machine-readable errors — what may client code branch on?

**Source:** Azure Handling Errors; Google AIP-193. **Question:** Which error fields are API contract vs debug-only?

## Stable identifier seam
**Azure shape:**
```http
HTTP/1.1 400 Bad Request
x-ms-error-code: UnsupportedApiVersionValue

{"error":{"code":"UnsupportedApiVersionValue","message":"…","target":"…"}}
```

**Google shape:** `google.rpc.Status` + required `ErrorInfo` `{ reason, domain, metadata }`; HTTP JSON uses `error.status` string + numeric HTTP `code`.

**Flow:** classify recoverable vs programmer-error → assign stable `code`/`reason` → put dynamic values in `metadata`/`innererror` (diagnostic, not contract) → human `message` brief and actionable.
**Invariant (Azure):** `x-ms-error-code` **equals** body `error.code` — customers compare these; values are **contract** (don't change meaning in-place).
**Invariant (Google):** `PERMISSION_DENIED` when auth fails **before** checking existence; `NOT_FOUND` only when caller had permission but resource missing (AIP-193).
**Probe:** contract tests assert stable codes for fixed failure modes; clients never regex-parse `message`; OpenAPI documents top-level codes only.

## Verdict
Adopt dual-layer errors (machine id + human message); adapt Azure header vs Google ErrorInfo; omit documenting message text as stable API. Learning note: `api-design-learning-note.md`.
