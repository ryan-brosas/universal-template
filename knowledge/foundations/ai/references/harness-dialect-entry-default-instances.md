<!-- capsule-v2 -->
# Dialect entry default instances — how do you give consumers a zero-config default without freezing the factory surface?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** how does each dialect package expose a ready-to-use harness while keeping full factory configurability?

## Package index.ts two-layer export
**Path/Symbol:** `packages/harness-cline/src/index.ts` (13L whole); identical shape in `harness-opencode/src/index.ts` (15L), `harness-claude-code/src/index.ts` (17L), `harness-codex/src/index.ts` (13L), `harness-pi/src/index.ts` (12L), `harness-deepagents/src/index.ts` (15L), `harness-grok-build/src/index.ts` (10L). **Signature:** `export const cline = createCline();` (module scope, no args).

### Decisive source
```ts
import { createCline } from './cline-harness';

/**
 * Default `cline` harness instance with no overrides — suitable for the
 * common case where the Cline SDK's defaults are fine. Equivalent to
 * `createCline()`.
 */
export const cline = createCline();

export { createCline } from './cline-harness';
export { VERSION } from './version';
export type { ClineHarnessSettings } from './cline-harness';
export type { ClineAuthenticationMode, ClineAuthOptions } from './cline-auth';
```

**Data Shape:** the default instance is a fully-formed `HarnessV1` (see the harness-v1 contract capsule) built once at module load with `settings = {}`; the factory stays exported for consumers that need auth, MCP servers, model overrides, or reasoning-effort settings. Types are exported separately from values so `import type` never pulls the runtime.

**Flow:** module import → `create<Name>()` runs at import time with empty settings → the returned `HarnessV1` object is frozen-in-time but lazy at the session level (auth resolution, bootstrap, and provider registration all happen inside `doStart`, not at instance creation) → consumers pass the instance straight into `new HarnessAgent({ harness: <instance>, ... })`.

**Invariant:** the default instance must never capture ambient secrets at import time — every credential decision is deferred to `doStart` (pass-29 auth-ladder capsules), so importing the package in a test or edge environment has no side effects beyond object construction.

**Probe:** `packages/harness-cline/src/cline-harness.test.ts` — `createCline()` with no args returns a `HarnessV1` whose `doStart` resolves auth lazily; the default-instance path is exercised by every `examples/harness-e2e-next/agent/harness/<dialect>/*.ts` example (`harness: claudeCode`, `harness: pi`, …).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createCline default instance export index", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: the seven package `index.ts` files surface together as the entry layer; the factories live one hop outbound.

## Verdict
Adopt the two-layer export (default instance + factory + types) for any plugin-style adapter package; adapt the doc-comment wording to your domain; omit nothing — the pattern is fully portable. Coverage caveat: no dedicated test imports the default instances (they are exercised through the e2e example app, which is not part of the unit suite); the factory path is what tests pin.
