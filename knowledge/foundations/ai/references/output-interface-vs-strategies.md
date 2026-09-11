<!-- capsule-v2 -->
# Output interface vs output-strategy — which structured-output abstraction should a porter take from this repo, and what does each mode's parse contract demand?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** The repo has BOTH `generate-text/output.ts` (the 4-method `Output` interface used by streamText/generateText) and the legacy `generate-object/output-strategy.ts` trio — which is canonical and what invariants does the interface carry per mode?

## Two abstractions, one winner
**Path/Symbol:** canonical: `packages/ai/src/generate-text/output.ts` (`interface Output` :22–58; factories `text` :66, `object` :93, `array` :197, `choice` :394, `json` :533). Legacy twin: `packages/ai/src/generate-object/output-strategy.ts:auto|tool|json` (:1–426), consumed by generate-object/stream-object only.
**Signature (canonical):** `{ name, responseFormat: PromiseLike<LanguageModelV4CallOptions['responseFormat']>, parseCompleteOutput({text}, ctx): Promise<OUTPUT>, parsePartialOutput({text}): Promise<{partial: PARTIAL} | undefined>, createElementStreamTransform(): TransformStream<EnrichedStreamPart, ELEMENT> | undefined }`.
**Data Shape:** legacy strategies instead return `{schema, injectPromises, transform}` — an older shape tied to generate-object internals; new code plugging into streamText MUST implement the 4-method interface, not the strategy.

### Decisive source
```ts
// choice.parsePartialOutput — prefix matching with ambiguity suppression:
if (result.state === 'successful-parse') {
  // successful parse: exact choice value
  return potentialMatches.includes(outerValue.result as any)
    ? { partial: outerValue.result as CHOICE }
    : undefined;
} else {
  // repaired parse: only return if not ambiguous
  return potentialMatches.length === 1
    ? { partial: potentialMatches[0] as CHOICE }
    : undefined;
}
```
(output.ts:503–513, verbatim)

```ts
// object.parsePartialOutput — NO validation of partials:
case 'repaired-parse':
case 'successful-parse': {
  return {
    // Note: currently no validation of partial results:
    partial: result.value as DeepPartial<OBJECT>,
  };
}
```
(:171–178)

**Flow (per mode):** `text` passes strings through untouched (default for every streamText call, even without `output`). `object` → json responseFormat + safeParseJSON + full schema validation on complete, raw DeepPartial (unvalidated!) on partial. `array` → `{elements}` envelope (envelope mechanics covered in `output-specification.md`) + per-element validation. `choice` → enum schema; complete requires exact membership; partial does live PREFIX matching against options, publishing only unambiguous prefixes during repair. `json` → parse-only, no schema.
**Invariant:** (1) Partial parses are NEVER schema-validated except array elements — UIs must render `DeepPartial` defensively. (2) Choice ambiguity (≥2 options share the prefix) publishes NOTHING rather than guessing. (3) Every complete-parse failure throws `NoObjectGeneratedError` carrying text/response/usage/finishReason so callers can debug from the error alone. (4) `parseCompleteOutput` receives finishReason because orchestrators gate parsing on it (finish ≠ tool-calls).
**Probe:** `packages/ai/src/generate-text/output.test.ts` — describes at :34/:86/:237/:500/:698 per factory; partial-validation absence pinned by object suites :184ff; choice ambiguity by :618ff.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "Output parsePartialOutput createElementStreamTransform", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ai", query: "output strategy auto tool json", limit: 5 });
```

## Verdict
Adopt the `generate-text/output.ts` interface as THE extension point (it composes with the enriched-stream publisher); treat `generate-object/output-strategy.ts` as legacy-shape reference for schema-injection techniques (prompt injection vs tool-call wrapping vs bare json mode). Adapt mode set to your product surface. Omit the legacy trio entirely if your host only streams via the interface. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
