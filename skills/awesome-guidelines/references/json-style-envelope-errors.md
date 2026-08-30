<!-- capsule-v2 -->
# Envelope and errors — does API responses follow data/error conventions?

**Source:** Google JSON style guide §JSON structure, §error object. **Question:** Do clients always get exactly one of `data` or `error` with stable reserved fields?

## Envelope seam
**Path/Symbol:** RPC/REST JSON responses using Google-style wrapper.
**Signature:** `apiVersion` present; `data` XOR `error` (error wins if both).
**Data Shape:** `kind` first in typed objects; `items` last in `data`.

### Success pattern
```json
{
  "apiVersion": "2.0",
  "context": "bart",
  "id": "1",
  "data": {
    "kind": "album",
    "title": "My Photo Album",
    "totalItems": 100,
    "items": [
      {
        "kind": "photo",
        "title": "My First Photo"
      }
    ]
  }
}
```

**Flow:** include `apiVersion` → put `kind` first in discriminated objects → collection metadata before `items` → `items` last in `data`.
**Invariant:** missing `apiVersion`, both `data` and `error`, or `items` before paging fields fail review.
**Probe:** contract tests assert envelope shape on success/error fixtures.

## Error pattern
```json
{
  "apiVersion": "2.0",
  "error": {
    "code": 404,
    "message": "File Not Found",
    "errors": [
      {
        "domain": "Calendar",
        "reason": "ResourceNotFoundException",
        "message": "File Not Found"
      }
    ]
  }
}
```

**Flow:** top-level `error` object → `code` + `message` → optional `errors[]` with domain/reason/details → never return success payload alongside error.
**Invariant:** empty error message or missing `code` on error responses fails review.
**Probe:** API tests cover 4xx/5xx JSON error shape.

## Reserved names seam
**Flow:** avoid using reserved names (`items`, `kind`, `apiVersion`, `error`, paging fields) for unrelated semantics → rename or bump major version on conflict.
**Invariant:** custom field named `items` holding non-array data fails review.
**Probe:** grep reserved list against OpenAPI property names.

## Verdict
apiVersion + data/error envelope, kind-first/items-last ordering, structured errors. Learning note: `json-style-learning-note.md`.
