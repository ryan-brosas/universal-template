<!-- capsule-v2 -->
# Version-injection bridge — how does a package embed its own version into runtime reports without importing package.json at runtime, keeping every build/test surface in parity?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How does a package embed its own version into runtime reports without importing package.json at runtime, keeping every build/test surface in parity?

## Build-time constant bridged through one ambient declare
**Path/Symbol:** `src/version.ts:CODEX_CONNECT_VERSION` (`:2-4`), defined by three build surfaces: `tsdown.config.ts:36-38` (node ESM) and `tsdown.config.ts:67-70` (browser CJS), plus `vitest.config.ts:9-11` (test runner).
**Signature:** `declare const __CODEX_CONNECT_VERSION__: string; export const CODEX_CONNECT_VERSION = __CODEX_CONNECT_VERSION__`.
**Data Shape:** A compile-time string constant. All three definers derive it from ONE package.json read using the byte-identical expression `JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).version` (`tsdown.config.ts:5-7` ≡ `vitest.config.ts:4-6`). Consumers read only the exported constant: `src/doctor.ts:102` (`report.version`) and `src/bin.ts:198` (`status --json` document).

### Decisive source
```ts
// src/version.ts (whole module, 4 lines)
/** Package version injected by the build and test configurations. */
declare const __CODEX_CONNECT_VERSION__: string

export const CODEX_CONNECT_VERSION = __CODEX_CONNECT_VERSION__

// vitest.config.ts :8-11 — the test surface carries its OWN define
export default defineConfig({
  define: {
    __CODEX_CONNECT_VERSION__: JSON.stringify(packageVersion),
  },
```

**Flow:** package.json → identical `readFileSync` derivation in tsdown ESM config, tsdown browser CJS config, and vitest config → per-surface `define` replaces the ambient identifier at bundle/eval time → modules import `CODEX_CONNECT_VERSION` → doctor/status JSON planes stamp it as `version`.
**Invariant:** Parity by construction, not by test — every surface derives from the same file read, so values cannot diverge while all three defines exist. Failure is fail-loud at module evaluation: any surface that forgets its define throws `ReferenceError: __CODEX_CONNECT_VERSION__ is not defined` at import time (of bin/doctor), failing every downstream suite — the green test baseline IS the executable proof for the vitest surface.
**Probe:** `tests/bin.spec.ts` (module-evaluates bin.ts under the vitest define; note the honest caveat below — no spec pins the injected VALUE).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", name_pattern: "CODEX_CONNECT_VERSION", limit: 10 });
// observed live: total 1 — dsh-codex.src.version.CODEX_CONNECT_VERSION Variable :4-4, in=2/out=0 (doctor.ts + bin.ts)
```
Graph caveats proven live: `trace_path(CODEX_CONNECT_VERSION, inbound)` reports callers_total=0 because USAGE edges are not CALLS edges (the variable's USAGE in-degree is 2); BM25 natural-language queries filter Variable nodes by design, so reachability runs through consumers (`doctorExitCode`, `doctorJson`).

## Verdict
Adopt the ambient-declare→export bridge plus one-derivation-per-surface twin defines for any bundler/test split where runtime `require('package.json')` is unwanted. Adapt define syntax to the host bundler and the derivation path to monorepo layout. Omit this repo's browser-CJS extras (`process.env.NODE_ENV` define at `:68`, `window.__ModuleLoader__.load(...)` banner/footer/intro `:71-76`) — they belong to the client packaging plane, not the bridge. Coverage caveat: check_index_coverage clean for src/version.ts, tsdown.config.ts, vitest.config.ts; NO spec pins the real injected value (doctor --json consumes a mocked report fixture; status --json asserts schemaVersion/package/status only).
