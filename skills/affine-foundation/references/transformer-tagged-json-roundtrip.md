<!-- capsule-v2 -->
# Tagged-payload JSON round-trip — how do rich Text/Boxed props survive a plain-JSON snapshot?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** Which prop values cannot ride through JSON directly, and what exact envelope tags revive them on import?

## `toJSON` / `fromJSON` with two magic markers
**Path/Symbol:** `blocksuite/framework/store/src/transformer/json.ts:6-30` (`toJSON`), :32-51 (`fromJSON`); markers in `src/consts.ts:4-5`.
**Signature:** `toJSON(value: unknown): unknown` / `fromJSON(value: unknown): unknown` — fully recursive over arrays and pure objects.
**Data Shape:** Tags: `TEXT_UNIQ_IDENTIFIER = '$blocksuite:internal:text$'` → `{ [TEXT]: true, delta: YDelta[] }`; `NATIVE_UNIQ_IDENTIFIER = '$blocksuite:internal:native$'` → `{ [NATIVE]: true, value: raw }`.

### Decisive source
```ts
// json.ts:13-18 — Text rides as its DELTA, never the Y.Text instance
if (value instanceof Text) {
  return { [TEXT_UNIQ_IDENTIFIER]: true, delta: value.yText.toDelta() };
}
// json.ts:36-42 — revival keys off Reflect.has, not truthiness
if (typeof value === 'object' && value != null) {
  if (Reflect.has(value, NATIVE_UNIQ_IDENTIFIER)) return new Boxed(Reflect.get(value, 'value'));
  if (Reflect.has(value, TEXT_UNIQ_IDENTIFIER))   return new Text(Reflect.get(value, 'delta'));
```

**Flow:** export: `_propsToSnapshot` (base.ts:45-58) maps ONLY `draftModel.keys` through `toJSON` (so sys keys and non-declared props never leak) → snapshot carries plain JSON. Import: `_propsFromSnapshot` (base.ts:37-43) maps every key back through `fromJSON`, rebuilding `Text` (fresh `Y.Text` seeded from delta) and `Boxed` wrappers; everything else deep-copies.
**Invariant:** (1) Detection uses `Reflect.has` — an envelope `{ '$blocksuite:internal:text$': false }` still revives as Text; porters filtering on truthy flags break empty-delta texts. (2) The marker strings are wire-format constants: renaming them invalidates every stored snapshot. (3) Round-trip is delta-preserving but NOT identity-preserving: a revived Text is a NEW Y.Text — doc equality must compare deltas, not references. (4) `isPureObject` guards the recursion so class instances that aren't Boxed/Text pass by reference untouched.
**Probe:** `grep -n 'NATIVE_UNIQ_IDENTIFIER\|TEXT_UNIQ_IDENTIFIER\|toDelta()\|new Text(' …json.ts …consts.ts | cut -d: -f1-2 | sort -u` → consts :4,:5; json :1,:9,:15,:16,:37,:40,:41. Direct tests: `transformer.unit.spec.ts:103-137` asserts revived `title`/nested `items[].content` are `instanceof Text` and render original strings after insertion into a live Y.Doc map.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "toJSON fromJSON text uniq identifier delta boxed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tagged envelopes for any CRDT-backed editor serializing to snapshots. Adapt tag spellings to your namespace but keep them out-of-band of user data. Omit the Reflect.has semantics and empty or false-flagged payloads silently degrade.
