<!-- capsule-v2 -->
# stringWiper + input masking wire format — why is the recorded value empty with a numeric mask?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What must a porter know about `SetInputValue(id, value, mask)` and text wiping so replayed fields show the right number of `*` instead of leaking the raw string?

## Mask-as-length, never mask-as-string
**Path/Symbol:** `tracker/tracker/src/main/app/sanitizer.ts` — `stringWiper` (:41–44), `Sanitizer.sanitize` (:132–149); `tracker/tracker/src/main/modules/input.ts` — `getInputValue` (:148–176).
**Signature:** `stringWiper(input: string): string`; `getInputValue(id, node): { value: string, mask: number }` where `mask = -1` (hidden), `>0` (length), or `0` (plain).
**Data Shape:** Wire message `SetInputValue(id, value: string, mask: number)`; `mask === -1` → field hidden entirely (`value: ''`); `mask > 0` → replay renders exactly `mask` asterisks; `value` itself carries content only in Plain mode.

### Decisive source
```ts
export const stringWiper = (input: string) =>
  input
    .trim()
    .replace(/[^\f\n\r\t\v\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff\s]/g, '*')
```
```ts
switch (inputMode) {
  case InputMode.Hidden:   mask = -1;        value = ''; break
  case InputMode.Obscured: mask = value.length; value = ''; break
}
return { value, mask }
```

**Flow:** `sanitize()` checks level ≥ Obscured → wipe every non-whitespace char (whitespace preserved to keep layout); otherwise optional `\d→0` (numbers) or email regex → per-part stars. Input module converts the level into `{value:'', mask}` — length is captured BEFORE clearing.
**Invariant:** Never send both a populated `value` and a mask: once masked, the raw string must be dropped client-side. The wiper's char class preserves all Unicode whitespace (not `\s`, which misses NBSP etc. — that's why the explicit class). `mask !== 0` doubles as the "was obscured" flag on `InputChange`.
**Probe:** `grep -c 'mask = value.length' tracker/tracker/src/main/modules/input.ts` → `1`; `grep -c 'mask = -1' tracker/tracker/src/main/modules/input.ts` → `1`; direct test `tests/sanitizer.unit.test.ts::should sanitize data as obscured if node is marked as obscured` pins `stringWiper` output equality (runner green).
**Coverage:** both files `no_recorded_issue`/`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "stringWiper getInputValue SetInputValue mask", limit: 10 });
```

## Verdict
Adopt mask-as-length wire semantics (bandwidth-cheap, no partial leaks). Adapt the wiper regex only if your target layout engine treats whitespace differently. Omit the legacy plain-text email star-split if you don't need it (the modern path wipes whole strings).
