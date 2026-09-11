<!-- capsule-v2 -->
# Native-mode cache-key partitioning — how do two incompatible cache universes share one restore-keys fallback chain?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** Docker-image runs and native CLI runs produce mutually incompatible caches. How can they never cross-restore while still falling back to stale-but-compatible entries?

## Boolean-embedded key prefix preserving prefix relationships
**Path/Symbol:** `common/qodana.ts:getNativeModePrefix` (:197-199), `isNativeMode` (:173-184); consumption `scan/src/utils.ts:getInputs` (:100-130).
**Signature:** `getNativeModePrefix(args: string[]): string` → `"native-true-"` | `"native-false-"`.
**Data Shape:** Input = parsed argv; Output = prefix prepended to BOTH `primaryCacheKey` and `additionalCacheKey`.

### Decisive source
```ts
export function getNativeModePrefix(args: string[]): string {
  return `native-${isNativeMode(args)}-`
}
// scan/src/utils.ts getInputs:
primaryCacheKey: nativePrefix + core.getInput('primary-cache-key'),
additionalCacheKey: nativePrefix + core.getInput('additional-cache-key'),
```

**Flow:** `getInputs` parses args FIRST → derives the boolean prefix → stamps it onto both keys → GitHub's `restoreCache([dir], primaryKey, [additionalKey])` matches the exact primary or any key sharing the additional prefix → a docker run can restore an older docker run's cache (prefix shared) but NEVER a native run's (prefix differs), and vice versa.
**Invariant:** The prefix must be applied to BOTH keys so the additional key remains a PREFIX of the primary key — that prefix relationship is what makes `restoreKeys` fallback work at all (test asserts `inputs.primaryCacheKey.startsWith(inputs.additionalCacheKey)`). Breaking the pairing silently corrupts analysis caches across modes.
**Probe:** `common/__tests__/main.test.ts` `describe('getNativeModePrefix')` :197-213 (empty args → native-false-, `--ide` → true, `--within-docker=false` single-token → true, split form → true); `scan/__tests__/utils.test.ts` :69-140 re-verifies through the real `getInputs` with mocked `@actions/core`, including the startsWith invariant.
**Coverage caveat:** restoreCaches/uploadCaches network paths are not exercised by tests; pinned via source ranges only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "getNativeModePrefix isNativeMode within-docker", limit: 6 });
```

## Verdict
Adopt "partition caches by mode with a boolean-embedded prefix on both primary and fallback keys" for ANY dual-mode tool cache (docker vs native is just one instance); adapt flag detection (`--ide`, `--within-docker[=]false`) to your tool's grammar; omit nothing else.
