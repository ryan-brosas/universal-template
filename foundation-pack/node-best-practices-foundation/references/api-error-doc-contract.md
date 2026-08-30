<!-- capsule-v2 -->
# API error-surface documentation — how do callers learn which failures to expect?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** What must an API document about its errors before callers can be correct?

## OpenAPI-declared status codes per condition; GraphQL schemas carry error guarantees natively
**Path/Symbol:** `sections/errorhandling/documentingusingswagger.md` (:5 REST premise + 409 example; GraphQL paragraph), (:13-42 GraphQL errors shape w/ message/locations/path), (:48 Joyent caller-contract quote).
**Signature:** OpenAPI response docs keyed by HTTP status (e.g. "409 when the customer name already exists"); GraphQL error object = `{message, locations:[{line,column}], path}` alongside `"data": {"film": null}`.
**Data Shape:** documented failure surface = status-code ↔ business-condition mapping (REST) or spec-defined error array (GraphQL).

### Decisive source
```text
# documentingusingswagger.md :5
it's absolutely required for the API user to be aware not only about the API
schema but also about potential errors – the caller may then catch an error
and tactfully handle it. For example, your API documentation might state in
advance that HTTP status 409 is returned when the customer name already exists
# :48 — why this is a correctness property
if you don't know what errors can happen or don't know what they mean, your
program cannot be correct except by accident.
```

**Flow:** design-time: enumerate failure conditions per endpoint → declare each as a documented status code (OpenAPI) or rely on GraphQL's schema-level error contract, optionally supplemented with comment docs → client tooling renders/handles them.
**Invariant:** an undocumented error is an unhandleable error — callers can only be "correct except by accident". Error documentation is part of the API SCHEMA, not release notes. Pairs with `error-detail-suppression` (document the CONDITION, never leak internals).
**Probe:** no runner upstream. Deterministic probe: `grep -cF 'status 409' sections/errorhandling/documentingusingswagger.md` >= 1 && `grep -c 'except by accident' sections/errorhandling/documentingusingswagger.md` >= 1 && `grep -c '"errors"' sections/errorhandling/documentingusingswagger.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "documentingusingswagger", limit: 5 });`

## Verdict
Adopt error-documentation-as-schema for every public endpoint. Adapt format (OpenAPI 3.x / GraphQL / gRPC status codes). Omit SWAPI example details.
