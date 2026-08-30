<!-- capsule-v2 -->
# position-write-validation — What values may a caller force into the ordering column?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** Which explicit position values pass validation, and which are rejected with what message shape?

## position-write-validation
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-args-processors/data-arg-processor/validator-utils/validate-overridden-position-field-or-throw.util.ts:validateOverriddenPositionFieldOrThrow` (:7-27).
**Signature:** `(value: unknown, fieldName: string): number | null` (throws CommonQueryRunnerException INVALID_ARGS_DATA).
**Data Shape:** accepts finite numbers only; sentinel strings ('first'/'last') never reach here — they are consumed upstream by RecordPositionService before validation.

### Decisive source
```ts
if (
  typeof value !== 'number' ||
  (typeof value === 'number' &&
    (isNaN(value) || value === Infinity || value === -Infinity))
) {
  const inspectedValue = inspect(value);
  throw new CommonQueryRunnerException(
    `Invalid position value ${inspectedValue} for field "${fieldName}"`,
    ...,
    { userFriendlyMessage: msg`Invalid value for position: "${inspectedValue}"` },
  );
}
```
(:10-22 — NaN and BOTH infinities rejected explicitly; `util.inspect` renders hostile values safely.)

**Flow:** type gate (number) → finiteness gate (NaN/±Inf) → throw with dual message (technical + userFriendly). This validator is invoked from DataArgProcessor's POSITION case (:181-182), i.e. AFTER RecordPositionService already resolved 'first'/'last'/backfill semantics — so by the time a value is validated it must be a concrete finite integer-ish number.
**Invariant:** ordering columns must never absorb non-finite floats (they poison min/max aggregates that gap-placement depends on). Error text embeds the inspected raw value for debuggability while the user-facing message mirrors it.
**Probe:** `grep -o 'Infinity' packages/twenty-server/src/engine/api/common/common-args-processors/data-arg-processor/validator-utils/validate-overridden-position-field-or-throw.util.ts | wc -l` → 2 (both signs on ONE line — plain `grep -c` returns 1 because it counts lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "validateOverriddenPositionFieldOrThrow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt finite-number-only admission for ordering columns plus the sanitize-side twin (`sanitizeNumber` collapses NaN/null reads to null). Adapt exception taxonomy; keep the inspect-based safe rendering of offending input. Omit nothing else — 20 portable lines.
