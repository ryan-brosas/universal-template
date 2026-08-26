<!-- capsule-v2 -->
# Canonical model-ref grammar — how does one string grammar serve both config validation and runtime destructuring?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** Where should the "provider/model" reference grammar live so normalization, routing, and provider lookup can never disagree?

## One first-slash parser, two call conventions
**Path/Symbol:** `extensions/config.ts:parseCanonicalModelRef` (:130–147). Graph fan-in hotspot: 15 inbound callers across config, provider, routing, and commands (trace both/d2).
**Signature:** `parseCanonicalModelRef(value: string): { provider: string; modelId: string }`.
**Data Shape:** Input is any string claiming to be a model ref. Returns split halves; THROWS on missing slash or empty half. No regex, no URL decoding.

### Decisive source
```ts
const slashIndex = value.indexOf('/');
if (slashIndex === -1) {
  throw new Error(`Invalid model reference "${value}". Expected "provider/model".`);
}
const provider = value.slice(0, slashIndex).trim();
const modelId = value.slice(slashIndex + 1).trim();
if (!provider || !modelId) {
  throw new Error(`Invalid model reference "${value}". Expected "provider/model".`);
}
return { provider, modelId };
```

**Flow:** FIRST slash splits — a model id may itself contain slashes (`openai/microsoft/phi` → provider `openai`, modelId `microsoft/phi`). Config-time callers (normalizeTierConfig, normalizeModelsMap, normalizeConfig's classifier arms) invoke it inside try/catch purely to VALIDATE and discard the result; runtime callers (buildRoutingDecision, streamSimple, resolveContextWindow/resolveMaxTokens) invoke it to DESTRUCTURE into provider+modelId for registry/auth lookups.
**Invariant:** The grammar is total over strings and total in behavior: either a clean split or a throw with the offending value embedded — never a silent mis-split. Whitespace-only halves count as empty (`'   /gpt-4o'` throws).
**Probe:** `extensions/config.test.ts` :179–202 (correct parse, missing slash, empty provider/modelId, whitespace-only provider).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "parseCanonicalModelRef invalid model reference", limit: 10 });
```

## Verdict
Adopt the single-grammar throw-based validator and its dual use (validate-and-discard at config time, destructure at runtime) verbatim; adapt the error message shape to your host's warning surfacing; omit regex hardening only if your providers genuinely allow arbitrary model ids — here permissiveness after the first slash is deliberate.
