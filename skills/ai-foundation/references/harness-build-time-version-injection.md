<!-- capsule-v2 -->
# Build-time version injection — how do you inject a package version into a client-identity string and keep the un-injected fallback testable?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** how does a package stamp its version into runtime identity when the bundler, not the source, owns the version?

## version.ts declare-and-fallback constant
**Path/Symbol:** `packages/harness-opencode/src/version.ts` (6L whole); byte-identical twins in `harness-claude-code`, `harness-codex`, `harness-cline`, `harness-pi`, `harness-deepagents` (md5 `3458cbe5b0ed5fc6aaa1649a56828535`); `harness-acp` and `harness-grok-build` differ only in formatting. **Signature:** `export const VERSION: string`.

### Decisive source
```ts
// Version string of this package injected at build time.
declare const __PACKAGE_VERSION__: string | undefined;
export const VERSION: string =
  typeof __PACKAGE_VERSION__ !== 'undefined'
    ? __PACKAGE_VERSION__
    : '0.0.0-test';
```

**Data Shape:** `__PACKAGE_VERSION__` is a bundler free-variable (declared, never imported) — `typeof` guarding keeps it legal when the define is absent (source-run tests, ts-node). Fallback `'0.0.0-test'` is a sentinel, not a lie: the grok-build snapshot test pins `expect(VERSION).toBe('0.0.0-test')`, so the un-injected path is itself a tested contract.

**Flow:** build tooling defines `__PACKAGE_VERSION__` from package.json → `VERSION` becomes the real version at bundle time → each dialect composes a client-app identity string at module scope (`const OPENCODE_CLIENT_APP = \`ai-sdk/harness-opencode/${VERSION}\`` in opencode-harness.ts :77, `GROK_BUILD_CLIENT_APP` in grok-build-harness.ts :19) → grok-build SPLITS the string (`split('/')`, pop the last segment, grok-build-harness.ts :288–308) into `{name: 'ai-sdk/harness-grok-build', version}` for config objects that need the fields separately → the identity travels to runtimes and gateways (grok-build interpolates it into `GROK_CLIENT_VERSION: { $source: 'client-app-version' }` gateway env, :339).

**Invariant:** the identity string format `ai-sdk/<package>/<version>` is the cross-runtime contract — splitting must keep the multi-segment name intact (join the popped array back with `/`), and the fallback must remain deterministic so tests never depend on build state.

**Probe:** `packages/harness-grok-build/src/grok-build-harness.test.ts` :221 (`expect(VERSION).toBe('0.0.0-test')`) and :107 (the `GROK_CLIENT_VERSION` gateway-env snapshot) — pins both the fallback value and the identity's consumption shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "__PACKAGE_VERSION__ VERSION client-app", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: the version.ts family plus the CLIENT_APP composition sites in each harness.

## Verdict
Adopt the declare-and-fallback free-variable pattern for any package whose version must appear in wire identity; adapt the sentinel value and the identity format to your own namespace; omit the gateway `$source` interpolation unless you have the same gateway contract. Coverage caveat: only grok-build pins VERSION directly; the other dialects' version constants are exercised indirectly through client-app strings in their harness tests.
