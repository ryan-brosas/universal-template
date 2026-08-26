<!-- capsule-v2 -->
# Tool fingerprinting — how do you detect MCP-style tool-definition drift ("rug pull") with a stable digest that never depends on function identity?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** Which tool fields are security-relevant enough to pin, and how is a function-valued description prevented from both breaking the hash and colliding with a string?

## fingerprintTools + detectToolDrift
**Path/Symbol:** `packages/ai/src/generate-text/tool-fingerprint.ts:fingerprintTools` (:30–45), `detectToolDrift` (:53–76); canonical hashing in `packages/ai/src/util/canonical-hash.ts:hashCanonical`.
**Signature:** `async function fingerprintTools(tools: ToolSet): Promise<Record<string, string>>`; `function detectToolDrift(current: Record<string,string>, baseline: Record<string,string>): { added: string[]; removed: string[]; changed: string[] }`.
**Data Shape:** Per-tool digest input = `{ description: {type:'string',value}|{type:'none'}|{type:'function'}, inputSchema: <resolved JSONSchema7>, title }`, fed to `hashCanonical`. Drift output classifies tools present in only one map (`added`/`removed`) vs digest mismatch (`changed`). Baseline capture/storage is explicitly the APP's concern.

### Decisive source
```ts
// tagDescription (:11-19): tagged shape keeps a literal string equal to some
// placeholder from ever hashing like a function.
function tagDescription(description: unknown) {
  if (typeof description === 'string') {
    return { type: 'string', value: description } as const;
  }
  if (description == null) {
    return { type: 'none' } as const;
  }
  return { type: 'function' } as const;
}
// detectToolDrift (:60-75): own-property lookups so a tool literally named
// `constructor` or `toString` diffs correctly.
for (const name of Object.keys(current)) {
  if (!Object.hasOwn(baseline, name)) added.push(name);
  else if (current[name] !== baseline[name]) changed.push(name);
}
for (const name of Object.keys(baseline)) {
  if (!Object.hasOwn(current, name)) removed.push(name);
}
```

**Flow:** At trust time (first connect / human review) compute `fingerprintTools` and store the map. On every later fetch recompute and diff: keys only in current → `added`; only in baseline → `removed`; same key different digest → `changed`. React (block/require re-approval) is the app's policy, not this module's.
**Invariant:** Only SERVER-controlled fields are pinned — a developer-owned function description is evaluated per call from local context, so only its PRESENCE is hashed (`{type:'function'}`), never its identity; otherwise unrelated refactors would flag phantom drift. All lookups must be own-property because tool names come from remote servers.
**Probe:** `packages/ai/src/generate-text/tool-fingerprint.test.ts` — identical defs identical digests (:17), schema-widen/title/description changes flip digest (:24/:41/:60), function-description identity ignored (:76/:86), `constructor`-named tool diffs correctly (:120).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "fingerprintTools detectToolDrift", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the field selection (string description presence+value, resolved input schema, title) and the tagged-shape trick for non-string descriptions; adopt own-property drift diffing verbatim. Adapt hash algorithm/canonicalization to host crypto conventions; omit baseline storage (app concern by design). Coverage caveat: best-effort index; excerpts read directly at HEAD.
