<!-- capsule-v2 -->
# Fireworks wire-id translation — how do public dots become wire `p`s across three serving namespaces?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you keep friendly catalog ids (`kimi-k2.6-turbo`) distinct from Fireworks/FirePass router wire forms?

## Lookbehind digit-guarded dot↔p codec + Fast-suffix serving-path split
**Path/Symbol:** `packages/catalog/src/fireworks-model-id.ts:toFireworksPublicModelId` (:9), `toFireworksWireModelId` (:13), FirePass twins (:20/:24), `FIREWORKS_FAST_SUFFIX` (:37), `isFireworksFastModelId` (:40), `toFireworksBaseModelId` (:44).
**Signature:** `toFireworksWireModelId(id): string` — idempotent (strips an existing prefix first); suffix helpers are prefix-aware.
**Data Shape:** prefixes `accounts/fireworks/models/` vs `accounts/fireworks/routers/`; transforms use lookbehind/ahead so ONLY digits surrounding the separator change.

### Decisive source
```ts
// (?<=\d)p(?=\d): version separators only — "qwen3p5" ↔ "qwen3.5" — while
// identifier-internal p's ("gpt-oss-120b") and non-digit contexts survive.
const VERSION_SEPARATOR_PATTERN = /(?<=\d)p(?=\d)/g;
const VERSION_DOT_PATTERN = /(?<=\d)\.(?=\d)/g;

// "Fast" is a higher-throughput SERVING PATH (dedicated router namespace,
// same weights, higher price, no priority tier) — a public-id suffix that
// translates at request time via compat.wireModelIdMode: "firepass".
```

**Flow:** catalog stores public ids → request time picks namespace by provider/variant (firepass or fireworks-fast ⇒ routers/, plain fireworks ⇒ models/) → dots→p's under the digit guard → response-side translation reverses it.
**Invariant:** (1) the codec must be its own inverse on prefixed inputs; (2) Fast variants collapse to their base for capability lookup but keep a distinct selector; (3) never rewrite dots in non-digit contexts.
**Probe:** coverage caveat: no dedicated unit file in this package pins the codec (translation is exercised indirectly through provider suites); contract anchored to lookbehind patterns + docs link in source.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "toFireworksWireModelId FIREWORKS_FAST_SUFFIX firepass routers", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt the digit-guarded codec pattern for any host that mangles ids into path segments; adapt prefixes to your namespaces; omit if your provider uses raw ids. Coverage caveat recorded above.
