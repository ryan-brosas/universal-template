<!-- capsule-v2 -->
# Code-mode execution policy byte expansion — how do friendly byte caps become runner limits without rejecting valid programs?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** When I configure `executionPolicy.maxToolOutputBytes`, what actually enforces it, and why does my valid output sometimes survive a "too big" nominal cap?

## Policy → limit translation layer
**Path/Symbol:** `packages/code-mode/src/run-code-mode.ts` — `resolveExecutionPolicy` (:174–192), `toRunLimits` (:359–383), `expandedSerializationLimit` (:385–390), `withSerializationOverhead` (:392–396), `isValidRunLimit` (:398–400), `translateLimitPath` (:679–699).
**Signature:** `expandedSerializationLimit(v) = min(MAX_RUN_LIMIT /* 2_147_483_647 */, max(4096, v * 2 + 1024))`; `maxSourceBytes: withSerializationOverhead(policy.maxSourceBytes, Buffer.byteLength(source) - Buffer.byteLength(userSource))`.
**Data Shape:** defaults (:49–58): timeoutMs 30_000, memory 64MiB, stack 2MiB, result 1MiB, console 64KiB, source 256KiB, toolInput 1MiB, toolOutput 4MiB, bridgeRequests 256, inFlightBridgeRequests 32.

### Decisive source
```ts
function expandedSerializationLimit(value: number): number {
  if (!isValidRunLimit(value)) return value;
  return Math.min(MAX_RUN_LIMIT, Math.max(4096, value * 2 + 1024));
}
// toRunLimits: maxHostFunctionArgumentsBytes: expandedSerializationLimit(policy.maxToolInputBytes),
//              maxHostFunctionOutputBytes: expandedSerializationLimit(policy.maxToolOutputBytes),
```

**Flow:** user policy resolved with defaults → source size asserted EARLY against the RAW policy (`assertSourceSize`, :194–202) → runner receives EXPANDED limits for result/toolInput/toolOutput and overhead-adjusted source limit (wrapper preamble bytes added on top, never subtracted from user budget) → code-mode still enforces the EXACT nominal caps itself via `toJsonPayload` at each boundary → runner-side `TypeError`s quoting internal paths are translated back to public names (`limits.maxHostFunctionArgumentsBytes` → `executionPolicy.maxToolInputBytes`, :687).
**Invariant:** the runner limits are SERIALIZATION BUDGETS (JSON escaping inflates payloads ~2×), not the user-facing contract — a porter who forwards `maxToolOutputBytes` verbatim into a sandbox bridge rejects valid outputs; enforcement of the exact number belongs on the host side of each boundary. Non-positive/non-integer limits pass through UNCHANGED (= disabled), they do not clamp to defaults (`isValidRunLimit` gate on every helper).
**Probe:** deterministic (anchored at repo root): `grep -n 'DEFAULT_MEMORY_LIMIT_BYTES = ' packages/code-mode/src/run-code-mode.ts` → `50:`; `grep -n 'value \* 2 + 1024' packages/code-mode/src/run-code-mode.ts` → `389:`; `grep -cF 'policy.maxResultBytes' packages/code-mode/src/run-code-mode.ts` → `3`; `grep -nF "'limits.timeoutMs':" packages/code-mode/src/run-code-mode.ts` → `681:`. Direct tests: `exceptions.test.ts:149-157` enforces `maxResultBytes: 4` on `'abcdef'`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "runCodeMode resolveExecutionPolicy", limit: 3 });` // verified live @9d9a73f: rank#1 runCodeMode :71-159, rank#2 resolveExecutionPolicy :174-192

## Verdict
Adopt the expand-on-the-way-down / enforce-exact-at-each-boundary split and the disabled-limit passthrough; adapt default numbers to your threat model; omit nothing — copying nominal caps straight into a VM bridge is the classic wrong port.
