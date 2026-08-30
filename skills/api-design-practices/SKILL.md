---
name: api-design-practices
description: "Use when designing or reviewing HTTP/JSON APIs — resource naming, idempotent writes, machine-readable errors, pagination from v1, and explicit versioning; distilled from Azure REST Guidelines and Google AIPs."
disable-model-invocation: true
---

# API Design Practices

Application skill for API design learning (`awesome-guidelines` deep ingest). Load learning note for *why*; capsules for probes.

## Core Principle

Public APIs are **contracts for retrying clients** — resource names stable, writes idempotent, errors machine-readable, lists paginated from day one, versions explicit.

## When to Use

- Designing new REST/JSON (or RPC+HTTP transcoding) endpoints.
- Reviewing OpenAPI/Proto HTTP bindings before GA.
- Adding list, error, or version behavior to existing APIs.

## When NOT to Use

- Internal-only in-process calls with no HTTP boundary.
- Stack already governed by a project-specific API standard — project wins; use this as gap analysis only.

## Workflow

1. **Model resources** — hierarchical names, plural collections, `name`/`parent` fields; acyclic refs (`api-design-resource-names.md`).
2. **Map verbs** — prefer Get/List/Create/Update/Delete; custom `:action` only when standard methods fail (AIP-121).
3. **Idempotent writes** — PUT/PATCH for create when possible; POST returns 201 + URL; repeatability keys for POST; 202 + LRO when async (`api-design-http-idempotency.md`).
4. **Errors** — stable `code`/`ErrorInfo.reason`; dynamic data in metadata; 403 before 404 on auth (`api-design-errors-machine-readable.md`).
5. **Lists** — ship pagination in v1; opaque `nextLink` or `page_token`; omit continuation on last page (`api-design-pagination-and-lists.md`).
6. **Version** — required `api-version` or documented equivalent; no silent breaking changes (`api-design-versioning-contract.md`).
7. **JSON** — camelCase fields (Azure); treat IDs as opaque strings; document enums as extensible when values grow.

## Red Flags

- Unbounded list returning all rows.
- Clients parsing error `message` text.
- POST create without idempotency story.
- Version only in URL path with no contract pin.
- 404 returned when caller lacks permission (information leak).
- Resource messages embedded inside other resources.

## Verification

- OpenAPI/Proto review checklist against five capsules.
- Contract tests: missing `api-version`, duplicate retry, pagination walk, stable error codes.
- Breaking-change review against version/deprecation rules.

## Skill Result Contract

```xml
<skill_result>
  <skill>api-design-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>OpenAPI/proto deltas, checklist against capsules</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>unpaginated list, unstable errors, non-idempotent POST, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/api-design-learning-note.md`
- `awesome-guidelines/references/api-design-resource-names.md`
- `awesome-guidelines/references/api-design-http-idempotency.md`
- `awesome-guidelines/references/api-design-errors-machine-readable.md`
- `awesome-guidelines/references/api-design-pagination-and-lists.md`
- `awesome-guidelines/references/api-design-versioning-contract.md`
