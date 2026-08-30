<!-- capsule-v2 -->
# remove-undefined-record-cleaner — Why must undefined be stripped before validation, and what survives the strip?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What does recursive undefined-stripping preserve vs drop on partial record inputs?

## remove-undefined-record-cleaner
**Path/Symbol:** `packages/twenty-server/src/engine/core-modules/record-crud/utils/remove-undefined-from-record.util.ts:removeUndefinedFromRecord` (:5-31).
**Signature:** `<T extends Record<string, unknown>>(record: T): T` (recursive, type-preserving).
**Data Shape:** input: partial record possibly carrying `undefined` sub-properties inside composite fields (LINKS, ADDRESS, ...); output: same shape minus every undefined leaf AND minus any nested object that became empty.

### Decisive source
```ts
if (value === undefined) { continue; }
// Recursively clean nested objects ... but preserve arrays as-is
if (typeof value === 'object' && !Array.isArray(value) && value !== null) {
  const cleaned = removeUndefinedFromRecord(value as Record<string, unknown>);
  if (Object.keys(cleaned).length > 0) { result[key] = cleaned; }
} else {
  result[key] = value;
}
```
(:11-27 — strict `=== undefined` check; empty-object pruning is a side effect of recursion.)

**Flow:** iterate entries → skip undefined → recurse into plain objects (not arrays, not null) → keep the nested key ONLY if something survived → everything else passes through. In-source comment (:1-4) states the WHY: "workflows/tools may pass partial composite fields with undefined sub-properties, but the validation layer expects either a value or null (not undefined)".
**Invariant:** `null` is NEVER stripped — it means "clear this field" and must survive to the writer; arrays pass untouched even if they contain holes/undefined members (documented "handled separately"); `{}` after cleaning is dropped entirely rather than sent as an empty composite. Distinguish from the deeper arg processor's own `if (isUndefined(value)) continue` (:155-157 of data-arg-processor) — both layers tolerate undefined but only this util prunes emptied composites.
**Probe:** `grep -c 'preserve null values so a field can be cleared' packages/twenty-server/src/engine/core-modules/record-crud/utils/__tests__/remove-undefined-from-record.util.spec.ts` → 1; direct spec asserts strip/null-preservation/nested-empty-drop/arrays-as-is.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "removeUndefinedFromRecord", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt undefined≠null discipline for partial writes plus empty-composite pruning. Adapt recursion guards to your language (cycles impossible here because inputs are JSON payloads). Omit nothing — this is a fully portable 30-line kernel.
