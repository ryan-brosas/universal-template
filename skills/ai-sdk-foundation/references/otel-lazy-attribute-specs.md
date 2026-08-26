<!-- capsule-v2 -->
# otel lazy attribute specs — how do you gate recordInputs/recordOutputs without paying serialization cost?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** How does the attribute selector defer expensive JSON.stringify of prompts/outputs until it knows the call actually records them?

## Path/Symbol
`packages/otel/src/select-attributes.ts:selectAttributes` (:19–65); `type AttributeSpec = AttributeValue | { input: () => … } | { output: () => … } | undefined` (:5–9).

**Signature:** `selectAttributes(telemetry, attributes: AttributeSpecMap): Attributes` — synchronous; the ASYNC variant with PromiseLike resolvers is `packages/otel/src/select-telemetry-attributes.ts:selectTelemetryAttributes` (:9–78, `await value.input()`, used by the legacy plane's sibling kernel in packages/ai).

**Data Shape:** an attribute map whose values are either plain OTel primitives/arrays, or thunks tagged by WHICH side they belong to: `{ input: () => AttributeValue | undefined }` for prompts, `{ output: () => … }` for completions.

### Decisive source
```ts
    if (
      typeof value === 'object' &&
      'input' in value &&
      typeof value.input === 'function'
    ) {
      if (telemetry?.recordInputs === false) continue;
      const resolved = value.input();
      if (resolved != null) {
        const sanitized = sanitizeAttributeValue(resolved);
        if (sanitized != null) result[key] = sanitized;
      }
      continue;
    }
```
(:32–44)

**Flow:** disabled telemetry short-circuits FIRST (`shouldRecord`: `telemetry?.isEnabled !== false` :13–17 → `{}`) so no thunk ever runs. Otherwise each entry: null → skip; input-thunk → skipped when `recordInputs === false`, else invoked NOW and sanitized; output-thunk → same under `recordOutputs`; plain value → sanitize-and-keep. Callers build the map inline at span creation, e.g. `'gen_ai.input.messages': { input: () => JSON.stringify(formatModelMessages(...)) }` (open-telemetry.ts :294–302) — stringify only executes inside `input()`.

**Invariant:** (1) The gate check happens BEFORE invoking the thunk — a porter who resolves-then-discards pays full serialization cost on every suppressed attribute, defeating the design. (2) Thunk returning `undefined` drops the key entirely (`if (resolved != null)`), which is how "no system instructions" / "empty messages" vanish from spans instead of emitting `"undefined"` strings. (3) Defaults are opt-OUT semantics: `isEnabled !== false`, `recordInputs === false` — i.e. everything records unless explicitly disabled. (4) Every resolved value passes through `sanitizeAttributeValue` even when the spec was a literal.

**Probe:** `grep -n "recordInputs === false" packages/otel/src/select-attributes.ts` → :37. `grep -c "input: () =>" packages/otel/src/open-telemetry.ts` → 19; `grep -c "output: () =>" packages/otel/src/open-telemetry.ts` → 10 (thunks outnumber literals ~2:1 in the new plane). Direct test: `select-telemetry-attributes.test.ts` (:38 "should not include input functions when recordInputs is false", :60 outputs, :82 undefined-returning resolvers drop keys), legacy twin suite `select-attributes.test.ts`.

**Retrieve:** live-resolved rank-1/2 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "selectAttributes sanitizeAttributeValue AttributeSpecMap", limit: 5 });
// → otel sanitizeAttributeValue 13-47, selectAttributes 19-65 (+ legacy in-file twin 66-118)
```

**Verdict:** ADOPT. The spec-map + deferred-thunk pattern ports anywhere you must honor per-call privacy flags over expensive payloads.
