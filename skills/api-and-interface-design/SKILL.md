---
name: api-and-interface-design
description: "Use when designing or reviewing REST/GraphQL APIs, SDK interfaces, or public module boundaries; choose contracts, failure semantics, and compatibility from consumer needs and project conventions."
invocation: entry
---

# API and Interface Design

This is the canonical API-design owner. `api-design-practices` remains a cold
compatibility entry, not a second rule set. Internal implementation changes with
no consumer-facing contract usually need only the normal engineering loop.

## Establish the contract that matters

1. Identify consumers, trust boundaries, deployment independence, existing
   conventions, and promised compatibility. Distinguish public HTTP APIs,
   internal services, GraphQL schemas, SDKs, and in-process modules.
2. Find the canonical description already maintained: source types, a schema,
   generated bindings, or documentation. Use schema-first when it helps multiple
   teams or generators; code-first can be appropriate when code generates the
   contract. Keep one owner and verify derived artifacts rather than requiring
   a new schema or generation tool for every interface.
3. Choose the smallest stable surface: inputs, outputs, resource ownership,
   lifecycle, failure/retry behavior, and any ordering or concurrency promises.
   Validate untrusted values at the responsible boundary; avoid redundant decoding
   inside trusted code.
4. Decide how consumers detect and recover from failures. Reuse their established
   error protocol, including standard framework shapes. Stable machine-readable
   distinctions matter when callers branch on them; a fixed four-field envelope,
   correlation field, or exception/result style is not universal. Do not expose
   secrets, internal paths, or stack traces to untrusted consumers.
5. Assess evolution against actual clients. Versioning, deprecation, idempotency,
   pagination, and quotas solve particular problems, not a checklist every API
   must implement. Explain important tradeoffs and preserve promised behavior.

## Load only the relevant detail

- HTTP methods, retries, errors, collections, and quotas:
  `references/rest-contracts.md`.
- GraphQL nullability, partial results, schema evolution, and query cost:
  `references/graphql-contracts.md`.
- Public modules, SDK ownership, errors, cancellation, and dependencies:
  `references/sdk-boundaries.md`.
- Compatibility assessment, version selection, and migration:
  `references/compatibility.md`.

Azure and Google API conventions are useful prior art, not interchangeable
universal standards. Their retained source capsules are linked from the REST
reference; load only those relevant to the chosen contract.

## Verify the consumer experience

Compare the exposed surface with its canonical description. Exercise representative
success and failure paths, boundary validation, and actual consumers. Add retry,
pagination, authorization, or compatibility tests only where that contract exists.
Check generated outputs if generation is used. Report untested integrations and
migration risks instead of inferring correctness from a schema alone.
