<!-- capsule-v2 -->
# Flat tool-schema near-miss repairs — why fabric_exec's model-facing schema stays flat and how `display`/`code`/null-params get repaired at the boundary

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for accepting model-shaped arguments at the fabric_exec boundary without a zero-work rejection round trip?

## Connected graph-selected seam
**Path/Symbol:** `src/fabric-exec-tool.ts` — flat-schema comment block (:110-120), `parameters` (:121-167), `prepareArguments` hook (:171-173); `src/fabric-exec-arguments.ts:prepareFabricExecArguments` (:14-41); `src/run-display.ts:normalizeRunDisplay` (:29-42); `src/type-error-guidance.ts:typeErrorRecoveryHint` (:6-15).
**Signature:** `prepareArguments(args)` runs in Pi's OFFICIAL pre-validation hook (NOT execute-time fallbacks — Pi validates custom-tool args before `tool_call`); `normalizeRunDisplay(input)` → `{ name?, description? } | undefined`; `prepareFabricExecArguments(input)` → prepared record.
**Data Shape:** legal display forms: object `{name?, description?}` / bare string / JSON-object string; `code`: string OR array-of-line-strings; optional keys `strings, resultFormat, tokenBudget, agentBudget, display`.

### Decisive source
```ts
    // The model-facing schema is intentionally flat: one large `code` string
    // plus scalar/optional params. Do not add nested arrays-of-objects with
    // escaped content here. SOTA models are post-trained on one dominant
    // harness's flat tool shapes and can invent trailing keys at the
    // highest-entropy point of a nested escaped-JSON field, which a strict
    // schema hard-rejects. Keep this surface string/scalar-heavy; the only
    // nested field (display) ignores unknown keys.
```
```ts
  if (Array.isArray(prepared.code) && prepared.code.every((line) => typeof line === "string")) {
    writable().code = prepared.code.join("\n");     // line-array near-miss
  }
  // null/undefined OPTIONAL keys are DELETED, not kept — strict schemas
  // reject explicit nulls on non-null fields.
```

**Flow:** three repair classes at one seam. (1) SHAPE policy: keep the tool surface flat because models hallucinate trailing keys inside nested escaped-JSON fields and strict validation then kills the whole call; the single nested field (`display`) tolerates unknown keys AND accepts bare-string/JSON-string spellings via `normalizeRunDisplay` (JSON-looking-but-invalid text like `{not json}` becomes `{ name: "{not json}" }` — intent preservation beats shape pedantry for a cosmetic label). (2) Coercions: line-array `code` joined; nullish optionals dropped; all inside `prepareArguments` so Pi's own validator sees clean input. (3) RESIDUE escape hatch: when payload text (edit/write content) still breaks TS syntax, `typeErrorRecoveryHint` detects pi.edit/pi.write + syntax-pattern errors and points at top-level `strings` + `π.key` instead of escaping inside code.
**Invariant:** repairs happen ONLY in prepareArguments (pre-validation), never as execute-time fallbacks; normalization never mutates the caller's object (copy-on-write `writable()`); an unusable display degrades to deletion or raw-name rather than rejection; type errors mean the program NEVER ran ("Type errors; code was not executed").
**Probe:** `tests/run-display.test.ts:20` ("repairs a bare objective string to { name }"), `:24` ("parses a JSON-stringified object, a common escaped-JSON near-miss"), `:28` ("falls back to the raw string when JSON-looking text is not a usable object"), `:30` ("returns undefined for empty and whitespace-only strings").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "prepareFabricExecArguments normalizeRunDisplay typeErrorRecoveryHint display", limit: 5, fields: ["signature", "name", "file"] });
```
