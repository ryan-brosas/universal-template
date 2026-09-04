<!-- capsule-v2 -->
# HarnessV1 adapter contract — what is the minimal portable contract for a third-party coding-agent adapter?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** how do you type an integration point so seven unrelated agent runtimes satisfy one interface without a capabilities matrix?

## The HarnessV1 type
**Path/Symbol:** `packages/harness/src/v1/harness-v1.ts:21` (`HarnessV1<TBuiltinTools>`); lifecycle payload types `packages/harness/src/v1/harness-v1-lifecycle-state.ts` (whole). **Signature:** `type HarnessV1<TBuiltinTools extends ToolSet = ToolSet> = { specificationVersion: 'harness-v1'; harnessId: string; builtinTools: TBuiltinTools; supportsBuiltinToolApprovals?: boolean; supportsBuiltinToolFiltering?: boolean; lifecycleStateSchema?: FlexibleSchema<unknown>; getBootstrap?: (...) => PromiseLike<HarnessV1Bootstrap>; doStart(options: HarnessV1StartOptions): PromiseLike<HarnessV1Session> }`.

### Decisive source
```ts
/**
 * Versioned specification for a harness adapter — the integration point for
 * one third-party coding-agent runtime (Claude Code, Codex, …).
 *
 * Modelled after `LanguageModelV4`: a tagged spec version, a small set of
 * descriptive fields, and one entry-point method (`doStart`) that yields a
 * session. There is intentionally no static "capabilities" object —
 * optional features are signalled by the presence or absence of optional
 * methods on the prompt-control handle. Adapters that cannot satisfy a request
 * (manual compaction not supported, required port exposure unavailable, …)
 * throw `HarnessCapabilityUnsupportedError` from the method that needs the
 * capability.
 */
export type HarnessV1<TBuiltinTools extends ToolSet = ToolSet> = {
  readonly specificationVersion: 'harness-v1';
  readonly harnessId: string;
  readonly builtinTools: TBuiltinTools;
  ...
  doStart(options: HarnessV1StartOptions): PromiseLike<HarnessV1Session>;
};
```

**Data Shape:** one literal spec tag (`'harness-v1'`, modelled after LanguageModelV4), one stable kebab-case id used as the key inside `HarnessV1Metadata` and for refusing mismatched lifecycle payloads, one `builtinTools` ToolSet keyed by what the bridge emits (`commonName ?? nativeName`), two OPTIONAL capability booleans, optional lifecycle-state schema, optional bootstrap recipe, ONE required method.

**Flow:** adapter package exports a `HarnessV1` (default instance or factory) → host (`HarnessAgent`) validates inbound tool calls against `builtinTools` merged with user tools → `doStart({sessionId, sandboxSession, sessionWorkDir, resumeFrom?|continueFrom?, permissionMode?, …})` yields a session → optional features are probed at the prompt-control handle at runtime; absence of a boolean degrades gracefully (adapters with approvals but no native filtering get inactive builtins auto-denied through the approval path — the documented fallback in the type's doc comment).

**Invariant:** there is deliberately NO static capabilities object — capability discovery is presence/absence of optional methods plus `HarnessCapabilityUnsupportedError` thrown from the method that needs the capability. Lifecycle payloads (`{harnessId, specificationVersion:'harness-v1', type:'resume-session'|'continue-turn', data: JSONValue}`) carry `harnessId` precisely so an adapter can refuse another dialect's state; `lifecycleStateSchema` promises exported `data` round-trips through a future `doStart`.

**Probe:** `packages/harness/src/v1/harness-v1-bridge-protocol.test.ts` and the per-dialect harness tests (e.g. `cline-harness.test.ts`) pin the `specificationVersion`/`harnessId` fields and the doStart option surface; `harness-v1-lifecycle-state.ts` types are exercised by every dialect's resume tests (e.g. cline-resume-state.test.ts schema cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "HarnessV1 specificationVersion doStart lifecycleStateSchema", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: harness-v1.ts first, then the seven create<Name> factories that satisfy it.

## Verdict
Adopt the tagged-spec + one-entry-method + capability-by-absence shape for any multi-runtime adapter layer; adapt the field set to your domain's session model; omit the bootstrap/lifecycle extensions if your runtime is stateless. Coverage caveat: no dedicated harness-v1.test.ts unit file exists — the contract is pinned through the dialect tests and the bridge-protocol test.
