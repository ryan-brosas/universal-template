# GraphQL contract choices

Start from the existing schema ownership and consumer tooling. SDL-first and
code-first generation are both viable; keep one canonical owner and check emitted
schema changes against actual operations.

- Nullability describes guarantees. A non-null field failure can propagate to its
  nearest nullable ancestor; test the partial-data/error behavior consumers see.
  Avoid stronger guarantees than the data and resolver lifecycle support.
- Distinguish execution errors from domain outcomes clients need to branch on.
  Reuse framework error handling, schema unions/objects, or documented extensions
  as appropriate. Do not force the REST reference's choices into GraphQL.
- Evolve schemas against stored/client operations. Removing fields, adding required
  inputs, or changing nullability can break clients. New enum/union variants may
  also affect exhaustive client handling. Deprecation helps only when consumers
  can discover and complete migration; URL-path versioning is not a default need.
- Choose pagination, batching, query-cost controls, and subscriptions from actual
  workloads. Connections are an option, not a universal list shape. Check resolver
  authorization for nested paths and batch/cache boundaries, not just root fields.
- Test representative operations, authorization, null/error propagation, and the
  relevant cost or pagination behavior. Schema validation alone does not prove
  resolver behavior or backward compatibility.
