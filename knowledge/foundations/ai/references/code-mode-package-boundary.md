<!-- capsule-v2 -->
# Code-mode package boundary — public API surface, run dependency, and the experimental_ naming convention

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What does `@ai-sdk/code-mode` export, what's external, and what stability contract do the names carry?

## Barrel + external `run` kernel
**Path/Symbol:** `packages/code-mode/src/index.ts` whole (:1–54); package.json (`"run": "^2.0.0"` sole runtime dep); tests import from `../dist/index.js` (built output, core.test.ts:5).
**Signature:** functions exported under `experimental_` prefix (runCodeMode, createCodeModeTool, codeModeTool, continueCodeModeInterrupt/Approval, getCodeModeApprovalResponse/CodeModeInterrupt, isCodeModeInterrupt/ApprovalInterrupt, unwrapCodeModeResult, requestCodeModeInterrupt, setCodeModeContinuationSigningKey, setMaxWorkers from 'run'); errors WITHOUT prefix; ~20 types.
**Data Shape:** zero side effects at import (`sideEffects:false`); module state limited to signing-key defaults + invocation counter + worker cap.

### Decisive source
```ts
export { setMaxWorkers as experimental_setMaxWorkers } from 'run';
export { requestCodeModeInterrupt as experimental_requestCodeModeInterrupt } from './host-interrupt.js';
// every test file: from '../dist/index.js'  — the CONTRACT is the built barrel
```

**Flow:** consumers either call `experimental_runCodeMode` directly for programmatic sandboxing or wire `experimental_codeModeTool` into generate calls; everything else (QuickJS worker pool, bridge protocol, interruption freeze) lives in the external `run` package — this repo layer is pure orchestration/policy/auth. The `experimental_` prefix on stable-in-practice APIs signals non-frozen protocol (continuation version field exists for the same reason: `version: 2` already encodes one breaking change). Tests exercise dist, not src, so tree-shaking/export shape is itself under test.
**Invariant:** a porter must keep the barrel as the only public path — deep imports bypass the experimental naming and would freeze internals prematurely. The single-dependency rule means any new capability needing VM semantics belongs in `run`, not here.
**Probe:** deterministic (repo root): `grep -cF 'extends CodeMode' packages/code-mode/src/errors.ts` → `10`; `grep -nF 'this.name = new.target.name' packages/code-mode/src/errors.ts` → `19:`; error sub-codes assigned post-super: `grep -nF "code = '" packages/code-mode/src/errors.ts` → lines 120/:140; barrel count check: `grep -cF 'export {' packages/code-mode/src/index.ts` → `7`; direct-test import anchor: `grep -nF "from '../dist/index.js'" packages/code-mode/src/core.test.ts` → `5:`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "DIRECT_TOOL_CALL requestCodeModeInterrupt", limit: 3 });` // verified live @9d9a73f: direct-tool-call + host-interrupt resolve line-exact in project ai

## Verdict
Adopt the orchestration-only layering with an external VM kernel and versioned continuation envelopes; adapt naming to your semver posture (drop `experimental_` only when the wire format is frozen); omit `run` internals (external, versioned).
