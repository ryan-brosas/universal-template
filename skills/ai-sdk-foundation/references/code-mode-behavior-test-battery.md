<!-- capsule-v2 -->
# Code-mode behavior test battery — the direct tests that pin sandbox, approval, and resume contracts

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Which tests are THE executable spec for code-mode behavior, and what does each pin that prose can't?

## Six suites, 50 tests
**Path/Symbol:** `packages/code-mode/src/core.test.ts` (7 its), `exceptions.test.ts` (17), `tool-invocation.test.ts` (12), `approval-continuation.test.ts` (6), `run-compatibility.test.ts` (3), `tool-prompt.test.ts` (5); all via `../dist/index.js` under vitest.
**Signature:** mocks (`vi.fn`) + `expect(execute).not.toHaveBeenCalled()` are the side-effect-free assertions; e2e haiku suite excluded (network).
**Data Shape:** runner requirement: built dist + zod/v4 + ai peer; `setMaxWorkers(32)` at core.test.ts:7 raises the process cap for parallel tests.

### Decisive source
```ts
// run-compatibility.test.ts:28-59 — resolutions pass through the SAME byte gate as outputs:
const options = { executionPolicy: { maxToolOutputBytes: 8 } };
...
).rejects.toThrow('exceeds the 8 byte size limit');   // :58
// approval-continuation.test.ts:146-204 — batched approvals resolve one-at-a-time,
// replay executes each tool EXACTLY once (:202-203 toHaveBeenCalledTimes(1)).
```

**Flow:** coverage map: core → execution semantics (fresh scope ×1 test, TS stripping ×2, JSON surface, 20-way parallelism); exceptions → every size gate + serialization semantics (Infinity→null, functions dropped, Date→ISO, circular input/output rejected pre-execute) + unknown/no-execute/validation errors; tool-invocation → proxy bridge (chained calls, undefined round-trip, async-iterable final part, host-clock restoration after awaits ≥30ms tolerance, context forwarding, abort propagation into nested tools) + late binding through a MOCK MODEL end-to-end; approval-continuation → callback mode, interrupt+replay with no double side effects, denial without execution, forged-envelope rejection, one-at-a-time batching, generic kinds; run-compatibility → non-identifier tool names, resolution size gating, legacy signing keys.
**Invariant:** the suite runs against BUILT output — a porter testing src directly isn't validating the shipped contract. The mock-model test (:190–245) is the only place the toolCaller wire format is pinned; deleting it desyncs description generation from reality silently.
**Probe:** deterministic (repo root): `grep -cF 'it(' packages/code-mode/src/exceptions.test.ts packages/code-mode/src/tool-invocation.test.ts` → per-file counts 17 and 12 (sum them); `grep -nF 'resolves.toEqual({ step: 2 })' packages/code-mode/src/tool-invocation.test.ts` → `85:`; `grep -nF 'rejects.toThrow(/Invalid input/)' packages/code-mode/src/exceptions.test.ts` → `45:`; `grep -nF 'rejects.toThrow(/Unknown tool: nope/)' packages/code-mode/src/exceptions.test.ts` → `16:`; `grep -nF "signingKey: 'legacy-key'" packages/code-mode/src/run-compatibility.test.ts` → `76:`. Real-runner status: NOT executed this window (no node_modules in inspo checkout); deterministic grep anchors above all live-verified instead.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "code mode core execution vitest", limit: 3 });` // verified family @9d9a73f: test files indexed as Module nodes under ai.packages.code-mode.src.*

## Verdict
Adopt this suite wholesale as the porting acceptance test; adapt imports to your build layout; omit the e2e network suite from CI gates.
