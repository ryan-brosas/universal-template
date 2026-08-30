<!-- capsule-v2 -->
# OSC 7777 automation-exit — how do I recover a command's exit code from the raw PTY stream?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How does the daemon learn a scheduled shell command's exit status when it ran inside an interactive PTY, surviving chunk splits and garbage bytes?

## Out-of-band exit signal + resumable chunk parser
**Path/Symbol:** `packages/server/src/utils/parse-osc-automation-exit.ts:parseOscAutomationExitFromChunk` (15–40); producer `packages/server/src/shell-hook-builder.ts:automationExitHookFunctionLines` (229–245) emitting `\e]7777;automation-exit;%d\a`; consumer `packages/server/src/session.ts:444-448`.
**Signature:** `parseOscAutomationExitFromChunk(data: string): number | null` (pure, stateless per call); session emits `"automation-exit": [code: number]`.
**Data Shape:** `ESC ] 7777 ; automation-exit ; <1..MAX_AUTOMATION_EXIT_CODE_DIGITS=4 decimal digits> ST`, ST = BEL (`\x07`) or ESC `\`. Payload >4 digits or non-numeric ⇒ that occurrence is skipped, not fatal.

### Decisive source
```ts
// :33-39 — skip malformed occurrences and KEEP SCANNING
searchFrom = terminatorIndex + 1;
```
with the accept gate at :31–32:
```ts
if (payload.length >= 1 && payload.length <= MAX_AUTOMATION_EXIT_CODE_DIGITS) {
  if (/^\d+$/.test(payload)) return Number.parseInt(payload, 10);
}
```

**Flow:** the shell hook runs the automation command via `eval` in the PROMPT hook, captures `$?`, and prints the OSC on the first prompt after completion — so the exit code rides the SAME output stream as the command, needing no side channel. The parser scans for the prefix, takes whichever terminator (BEL vs ST) comes first, validates the payload, and on any malformed occurrence resumes scanning AFTER its terminator so noise before the real signal never blocks it. Session-level: parsing is gated on `reportInitialCommandExit && !hasEmittedAutomationExit` (session.ts:443-446) — exactly one emit per session, since the hook fires on the first prompt only. The composition root's `onAutomationExit` (index.ts:2214) turns code 0 into "completed" else "failed", attaches the redacted log, closes the run tab if closeOnFinish, and notifies watch/event managers.
**Invariant:** the hook copies LOCALTERM_INITIAL_COMMAND into a local and UNSETS the env var BEFORE eval — the command string is not inherited by children and the hook can't re-run; the variable is also on PTY_ENV_DENYLIST so only the constructor's set is a source. Exit codes are bounded at 4 digits because real codes are ≤255; longer payloads are garbage by construction.
**Probe:** `packages/server/tests/utils/parse-osc-automation-exit.test.ts` — BEL/ST termination (:5/:11), embedded-in-output (:15), ignores git-dirty (:20), unterminated ⇒ null (:24), non-numeric/oversized ⇒ null (:28), `"skips a malformed occurrence and parses a later valid one"` (:34).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "parseOscAutomationExitFromChunk buildAutomationSecretEnv", limit: 6, detail: "compact" });
// → parseOscAutomationExitFromChunk @ parse-osc-automation-exit.ts:15-40
await mcp.codebase_memory.search_graph({ project: "localterm", query: "automationExitHookFunctionLines LOCALTERM_INITIAL_COMMAND", limit: 5, detail: "compact" });
```

## Verdict
Adopt the private OSC channel + copy-unset-eval hook pattern verbatim whenever commands run inside interactive shells (the only reliable way to get exit codes AND keep the PTY interactive); adapt the channel number/prefix to host; omit the ST branch if your terminal family only ever emits BEL. 7 direct tests pin the parser byte-for-byte at this commit.
