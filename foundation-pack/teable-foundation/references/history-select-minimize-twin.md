<!-- capsule-v2 -->
# Select-choice minimization twin (v1/v2)

## Source / Question
**Source:** teable `apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts` `minimizeFieldOptions` (:146–173) and `apps/nestjs-backend/src/features/v2/v2-record-history.service.ts` module-level `minimizeFieldOptions` (:218–243).
**Question:** Why is the select-field options object FILTERED at history-write time, and what are the exact value-shape branches?

## Path / Symbol
Both copies: `minimizeFieldOptions(value, field|meta)` — gated on `SELECT_FIELD_TYPE_SET.has(type)` where the set = {SingleSelect, MultipleSelect} (module-level const in BOTH files).

## Signature
```ts
(value: unknown, field: { type; options: Record<string,unknown>|null }) =>
  Record<string, unknown> | null | undefined   // returns FULL options with choices REPLACED
```

## Data Shape
`options.choices: { id, name, color }[]`; v1 listener reads options from the DB Field row (`rawField2FieldObj`), v2 builds a COMPAT-SHAPED options object `{ choices }` only (visitor returns null for all other field types — 20 `return ok(null)` sites).

## Decisive source
```ts
if (value == null)      return { ...options, choices: [] };
if (isString(value))    return { ...options, choices: choices.filter(({name}) => name === value) };
if (Array.isArray(value)) {
  const valueSet = new Set(value);
  return { ...options, choices: choices.filter(({name}) => valueSet.has(name)) };
}
return _options;   // non-select types: options pass through untouched (v2: null)
```
(listener :158–172; v2 :228–242 — line-for-line twin)

## Flow / Invariant
1. **Choices are filtered to the VALUE, not to "choices that existed at the time"**: if a choice was deleted from the field after the cell was set, the history row's options lose that choice too. The snapshot answers "what did this cell say", NOT "what did the palette look like" — deliberate storage minimization.
2. **null/undefined value → empty choices array**, never undefined choices — so JSON always has a stable `choices` key for select fields.
3. **Multi-select uses Set membership against choice NAME** (not id): duplicate names collapse; order follows the OPTIONS list, not the value list.
4. **The twin is intentional duplication across engines** (v1 has no access to v2 domain objects and vice versa); a porter should copy ONE file's version per engine rather than invent a shared util that couples the engines.
5. **v2's visitor returns options ONLY for the two select field types** — 20 explicit `visit*Field(): ok(null)` arms make the compat surface exhaustive against future field-type additions (compiler-forced).

## Probe (direct tests)
Anchored at repo root:
```bash
grep -c 'return ok(null)' apps/nestjs-backend/src/features/v2/v2-record-history.service.ts   # → 20
grep -c minimizeFieldOptions apps/nestjs-backend/src/event-emitter/listeners/record-history.listener.ts  # → 3 (def + 2 call sites)
grep -cF 'valueSet.has(name)' apps/nestjs-backend/src/features/v2/v2-record-history.service.ts           # → 1
```

## Retrieve
```bash
codebase-memory-mcp cli search_code '{"project":"teable","pattern":"FieldOptionsVisitor","limit":3}'
# → Class .../features/v2/v2-record-history.service.ts 111-192 (+ extractFieldMeta call site :209)
```

## Verdict
**adopt** — value-shaped option snapshots are the reusable contract; port with the three-branch ladder intact and per-engine duplication preserved.
