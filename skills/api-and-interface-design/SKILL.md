---
name: api-and-interface-design
description: Use when designing REST/GraphQL APIs, SDK interfaces, or public module boundaries, covers contract-first design, versioning, error shapes, and backward compatibility
---


# API & Interface Design

## Core Principle

Contract first, implementation second, the API is the contract; internal code can change freely, the contract cannot.

## When to Use / NOT

- **Use when:** designing REST/GraphQL APIs, SDK interfaces, or public module boundaries, contract-first design, versioning, error shapes, backward compatibility.
- **NOT when:** N/A, no explicit exclusion stated in this skill.

## Workflow

1. Write the schema (OpenAPI, GraphQL SDL, Protobuf, JSON Schema).
2. Generate types from the schema (client + server).
3. Validate at the boundary (decode unknown → typed value).
4. Implement against the types, never raw input.
5. Choose a versioning strategy; shape errors (code, message, details, traceId); add idempotency, pagination, and rate-limit headers.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **Contract first, implementation second.** The API is the contract. Internal code can change freely; the contract cannot.
- **Version explicitly.** `/v1/`, `/v2/`, or header. Implied versions break unexpectedly.
- **Errors are part of the contract.** Shape them as deliberately as the success response.
- **Backward compatibility is a feature.** Breaking changes cost users; every break must justify.
- **Document what you ship, not what you intended.** Generated docs from the schema, not hand-written.
</EXTREMELY-IMPORTANT>

## Contract-First Design

1. **Write the schema** (OpenAPI, GraphQL SDL, Protobuf, JSON Schema).
2. **Generate types** from the schema (client + server).
3. **Validate** at the boundary (decode unknown → typed value).
4. **Implement** against the types, not the raw input.

Never let a request body reach the implementation as `any` or `unknown`. Decode first.

## Versioning Strategy

| Strategy | When |
|-------------------------------------------------|---------------------------------------------------|
| URL path (`/v1/`, `/v2/`) | Public API, multiple versions live simultaneously |
| Header (`Accept: application/vnd.api+json;v=2`) | Internal API, more flexible |
| Query param (`?v=2`) | Web-only, simple cases |
| None (breaking is breaking) | Internal-only, single consumer |

For public APIs, prefer URL path. It's visible, cacheable, and easy to reason about.

## Error Shape

```json
{
  "error": {
    "code": "user_not_found",
    "message": "User 123 not found",
    "details": { "userId": "123" },
    "traceId": "abc-def-ghi"
  }
}
```

Always: machine-readable `code` (stable, never localized), human-readable `message` (localized OK), `details` (structured context), `traceId` (correlation). Never: stack traces, internal paths, secrets.

## Backward Compatibility

**Add only.** Never change existing field meanings. Avoid tightening validation or removing fields. Do not rename.

If you must break: new version, deprecation period, migration guide, codemod if possible.

## Idempotency

`PUT` should be idempotent. `POST` for creation can be made idempotent with an `Idempotency-Key` header. `DELETE` should be idempotent. The client should be able to retry safely.

## Pagination

Prefer **cursor-based** for feeds and large lists. Skip-relations are slow on big tables. Return a `nextCursor` and `hasMore`. Document the cursor format if you can.

## Rate Limiting

Return headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` (on 429). Make limits visible. Document them.

## Common Mistakes

Schema after impl (backwards); no version; generic errors; no idempotency; no pagination (returns 10k items); no rate limit headers; breaking without bump; hand-written docs; field reused for new purpose; no `traceId`; asymmetric shapes.

## Red Flags

`/api/` (no version); error as string; no idempotency; no pagination; no rate limit; hand-written docs; breaking in minor; field reused; no `traceId`; "schema is in the code".

## Anti-Patterns

**Schema after impl**; **no version**; **generic errors**; **breaking without bump**; **hand-written docs**; **no idempotency**; **no pagination**; **silent breaking**.

## Verification

Generated docs from the schema match what you ship; every error carries machine-readable `code`, human-readable `message`, `details`, and `traceId`; version is explicit; rate limits visible via headers; no stack traces, internal paths, or secrets in responses.

## Skill Result Contract

```
<skill_result>
  <skill>api-and-interface-design</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Schema written, types generated, boundary validation in place; generated docs match shipped API</evidence>
  <artifacts>API contract: schema, versioning strategy, error shape, idempotency, pagination, rate limits</artifacts>
  <risks>Unversioned breaks, generic errors, hand-written docs, or none</risks>
</skill_result>
```

## References

N/A, no reference files; this skill is self-contained.
