<!-- capsule-v2 -->
# Audit logging middleware split (per-event factories)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/logging.py` (whole file, 67L).

## Path/Symbol
- `audit_log_pre_tool()` (:21) — ToolCallContext
- `audit_log_post_tool()` (:29) — 200-char result/error summary
- `audit_log_post_turn(level=INFO)` (:42) — counts of calls/results/messages
- `audit_log_post_agent(level=INFO)` (:56) — success/error/output summary

## Signature
Four independent factories, one per lifecycle event, each returning the standard async `(ctx, next_fn)` middleware.

## Decisive source
```python
# Split into one factory per lifecycle event (rather than one class
# implementing four Hook methods) since each is now registered on its own
# pipeline; ControlPlane registers whichever of these it wants, in whichever
# combination, instead of one hook object bundling all four.
```

## Invariant
Legacy hook OBJECTS bundled every event; the kernel's per-event pipelines make per-event FACTORIES the right unit — composition is a la carte, and no logger can accidentally ride an event it doesn't declare.

## Probe
No dedicated unit test (logging-only behavior; coverage caveat). Deterministic check: each factory is a pure observer — mutates nothing, always awaits `next_fn()`.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["audit_log_pre_tool","audit_log_post_turn"]'`

## Verdict
ADAPT (small but load-bearing): the class→per-event-factory migration pattern applies to any legacy hook bundle being ported onto this kernel.
