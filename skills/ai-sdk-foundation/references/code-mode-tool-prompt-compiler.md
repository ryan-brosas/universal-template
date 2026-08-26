<!-- capsule-v2 -->
# Code-mode tool-prompt compiler — JSON Schema to TypeScript declaration + example synthesis for the model

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How is the `tools.*` API surface rendered into the code-mode tool description the model reads?

## Schema → type renderer with depth/ref guards
**Path/Symbol:** `packages/code-mode/src/tool-prompt.ts` — `buildCodeModeToolDescription` (:15–55), `renderToolType` (:57–80), `renderToolExamples` (:82–111), `schemaToTypeInner` (:186–262), `objectType` (:264–312), `arrayType` (:314–332), `sampleFromSchemaInner` (:342–441), `resolveRef` (:449–471), `compactObjectType` (:541–553), constants :12–13.
**Signature:** `MAX_SCHEMA_DEPTH = 8`; `MAX_COMPACT_OBJECT_TYPE_LENGTH = 120`; empty toolset ⇒ `'No host tools. Do not call \`tools.*\`.'`.
**Data Shape:** renderer context `{root, seenRefs:Set, depth}` — `$ref` cycles tracked per-render via seenRefs (resolveRef refuses non-`#/` refs and repeats), depth overflow degrades to `'unknown'` (types) / `null` (samples).

### Decisive source
```ts
const sections = [
  'Execute code-mode TypeScript in an isolated sandbox.', '',
  'Put the full program in `js`; top-level `await`/`return` work. ...',
  'Call host tools only as async `tools.name(input)`; await each or use `Promise.all` ...',
  ...
  'Fetch: `fetch` is not available.',
];
```

**Flow:** each tool renders a doc-comment (description ?? title, `*/` defanged) + `name: (input: T) => Promise<U>;` line; multi-tool examples become `const [a,b] = await Promise.all([...])` with per-tool destructuring projections of the FIRST output property (:124–133); single-tool examples return the projection directly. Type mapping: const/enum → literal unions, oneOf/anyOf → union, allOf → intersection, arrays with tuple items → `[A,B]`, additionalProperties → index signatures, required-ness → `?`. Sample values: schema `default` first, then enum[0]/oneOf[0], then format-aware strings (`uri`→example.com, `date-time`→2026-01-01T00:00:00.000Z), numbers→1, booleans→true; explicit `inputExamples[0].input` wins over everything (:443–447). Compact one-line object types only when ≤120 chars AND no doc comments.
**Invariant:** the description is a CONTRACT with the generated preamble (proxy-bindings capsule): it promises `tools.name(input)` arity and Promise.all parallelism — a porter who changes call arity in the preamble without regenerating this text desyncs model expectations from runtime. Async jsonSchemas (promise-like) degrade to `unknown` rather than hanging description build.
**Probe:** deterministic (repo root): `grep -nF 'MAX_SCHEMA_DEPTH = ' packages/code-mode/src/tool-prompt.ts` → `12:`; `grep -nF 'No host tools. Do not call' packages/code-mode/src/tool-prompt.ts` → `19:`; `grep -nF "is not available" packages/code-mode/src/tool-prompt.ts` → `45:` ('Fetch: `fetch` is not available.'); `grep -nF "seenRefs.has(ref)" packages/code-mode/src/tool-prompt.ts` → `454:`; `grep -cF 'nextContext(context)' packages/code-mode/src/tool-prompt.ts` → `14`; `grep -nF 'Promise.all([' packages/code-mode/src/tool-prompt.ts` → `101:`; `grep -nF 'inputExamples' packages/code-mode/src/tool-prompt.ts` → `444:`. Direct tests: tool-prompt.test.ts 5 its cover description/examples/type rendering.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "buildCodeModeToolDescription schemaToType sampleFromSchema", limit: 4 });` // verified live @9d9a73f: schemaToType :178-184, sampleFromSchema :334-340, buildCodeModeToolDescription :15-55

## Verdict
Adopt depth-capped, cycle-safe schema rendering and format-aware example synthesis; adapt section prose to your own sandbox's capabilities (the fetch disclaimer must match reality); omit nothing.
