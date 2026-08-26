<!-- capsule-v2 -->
# Code-mode error taxonomy — code-preservation channel, stack translation, and the RunError mapping table

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How do typed errors survive the worker bridge, and why do user-visible messages name `executionPolicy.*` and `code-mode.js` instead of internals?

## Code-keyed preservation + two-layer message laundering
**Path/Symbol:** `packages/code-mode/src/errors.ts` whole (:7–142, 10 `extends CodeMode` classes); `packages/code-mode/src/run-code-mode.ts` — `findPreservedCodeModeError` (:613–621), `toCodeModeRuntimeError` (:623–677, 8 RUN_* cases + default), `translateLimitPath` (:679–699), `copyStack` (:701–706), `translateSourceStack` (:708–718).
**Signature:** every CodeModeError carries stable `code` (`CODE_MODE_TIMEOUT`, `CODE_MODE_ABORTED`, `CODE_MODE_CONCURRENCY_LIMIT`, `CODE_MODE_SOURCE_TOO_LARGE`, `CODE_MODE_BRIDGE_LIMIT`, `CODE_MODE_DETACHED_BRIDGE_REQUEST`, `CODE_MODE_PROTOCOL_ERROR`, `CODE_MODE_TOOL_ERROR`, sub-codes `CODE_MODE_TOOL_APPROVAL_REQUIRED/_DENIED`) + optional `details`.
**Data Shape:** host side pushes thrown CodeModeErrors into a per-invocation `codeModeErrors[]`; RunErrors are rethrown with `(message, code, details)` triple.

### Decisive source
```ts
function findPreservedCodeModeError(error, errors) {
  if (!RunError.isInstance(error)) return undefined;
  return errors.find(candidate => candidate.code === error.code);
}
// throw path:
const preserved = findPreservedCodeModeError(error, codeModeErrors);
if (preserved !== undefined) throw translateSourceStack(preserved);
throw translateSourceStack(toCodeModeRuntimeError(error));
```

**Flow:** sandbox/host error → wrapped as RunError(code) crossing the bridge → catch: first try matching a locally-thrown CodeModeError BY CODE (restores class instance + details); else map RUN_* codes to typed classes (RUN_ABORTED/TIMEOUT/CONCURRENCY_LIMIT/SOURCE_TOO_LARGE/BRIDGE_LIMIT/DETACHED_BRIDGE_REQUEST/PROTOCOL_ERROR), copying the ORIGINAL stack via copyStack; bare TypeErrors get limit-path rewriting; SyntaxErrors without syntax-y words get prefixed. Finally ALL stacks have `run.js:L:C` frames rewritten to `code-mode.js:(L-1):C` (SOURCE_LINE_OFFSET=1 compensates the preamble's added first line) so the model sees line numbers in ITS coordinate system. Non-Error host throws become generic `'Host tool failed.'`.
**Invariant:** code-matching is per-INVOCATION state (array captured in closure), not global — concurrent runs can't cross-contaminate. A porter who preserves only the message loses the class (instanceof checks in tests break); one who skips stack translation ships un-actionable line numbers pointing into generated code.
**Probe:** deterministic (repo root): `grep -n 'errors.find(candidate' packages/code-mode/src/run-code-mode.ts` → `620:`; `grep -cF 'copyStack(' packages/code-mode/src/run-code-mode.ts` → `7` (6 call sites + 1 def... actual: 6 case calls + def = 7 occurrences); `grep -nF 'HostFunctionInterruptSignal' packages/code-mode/src/run-code-mode.ts` → `337:` (interrupt signals rethrown raw, never wrapped); `grep -oF 'copyStack(new CodeMode' packages/code-mode/src/run-code-mode.ts | wc -l` → `6`; `grep -nF 'run\.js:' packages/code-mode/src/run-code-mode.ts` → `713:`; `grep -nF 'function translateSourceStack' packages/code-mode/src/run-code-mode.ts` → `708:`; `grep -cF 'extends CodeMode' packages/code-mode/src/errors.ts` → `10`; direct test anchors exceptions.test.ts:16/:45/:80/:89.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "CodeModeProtocolError translateLimitPath", limit: 3 });` // verified family live @9d9a73f via run-code-mode anchors; errors.ts classes are graph-visible Module members

## Verdict
Adopt code-keyed preservation, per-invocation error registries, and source-coordinate stack translation as one unit; adapt your RUN_* → public-class table; omit nothing — each layer fixes a distinct porter trap.
