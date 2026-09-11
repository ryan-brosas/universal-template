# SDK and public-module boundaries

Identify consumers and lifecycle ownership before adding abstraction. An SDK may
hide protocol details; an in-process module may need only a few stable exports.
Neither automatically needs an HTTP schema, version endpoint, or rate-limit fields.

- Prefer the project's canonical types and package/export conventions. Generate
  clients when generation reduces drift; hand-maintained interfaces are valid
  when small and tested against the underlying behavior.
- State resource ownership: who opens/closes clients, owns streams, controls
  cancellation, and configures timeouts. Avoid global mutable configuration when
  independent consumers need different settings.
- Follow ecosystem failure semantics: exceptions, rejected promises, results, or
  another established contract. Distinguish actionable failures without leaking
  transport internals or sensitive implementation details unnecessarily.
- Define retries explicitly. Automatic retries can duplicate writes or multiply
  retries already performed by callers. Expose cancellation and partial completion
  where meaningful; do not imply atomicity across unrelated remote operations.
- Keep public dependencies and exported types deliberate. Adding a wrapper around
  every dependency can create more surface than it hides; use one when it provides
  useful isolation, adaptation, or compatibility ownership.
- Verify from a consumer: import/build a representative client, exercise lifecycle
  and error paths, and compare published exports/types with promised compatibility.
  Select migration/version rules from `compatibility.md`.
