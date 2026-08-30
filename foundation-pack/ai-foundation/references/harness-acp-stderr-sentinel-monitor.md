<!-- capsule-v2 -->
# ACP stderr sentinel monitor — how do you detect an agent that failed WITHOUT its RPC ever failing?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** An ACP agent can hit a provider-stream decoding failure, log it to stderr, and keep its pending JSON-RPC prompt hanging forever — the protocol never rejects. How does the bridge fail the turn instead of waiting indefinitely?

## Line-buffered stderr pump that IS the failure promise
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/agent-stderr-monitor.ts` — `monitorACPAgentStderr` (:4–52, sentinel branch :36–50); wiring `bridge/index.ts` :401–412 (monitor over child.stderr, per-line bridgeLog), :146–152 (runTurn hard-requires a monitor), :296–300 (raced in the turn's failure set).
**Signature:** `monitorACPAgentStderr({ stderr, onStderrLine }: { stderr: Readable; onStderrLine: (line: string) => void }): Promise<never>`.
**Data Shape:** returns a `Promise<never>` that rejects ONLY on (a) the stderr stream itself erroring, or (b) the sentinel match. Sentinel: lowercased `stripVTControlCharacters(line)` contains `'failed to deserialize responsestreamevent from stream'`. Empty lines are skipped; the pump is line-buffered (split on `\n`, trailing partial retained across chunks, flushed at stream end).

### Decisive source
```ts
// agent-stderr-monitor.ts:36–50 — the comment is the design rationale
/*
 * An ACP agent can log a response-stream decoding failure without rejecting
 * its pending JSON-RPC prompt. Once the provider stream cannot be decoded,
 * no valid prompt completion can reach the ACP client, so the bridge must
 * fail the turn instead of waiting indefinitely.
 */
if (
  normalizedLine
    .toLowerCase()
    .includes('failed to deserialize responsestreamevent from stream')
) {
  rejectFailure(
    new Error('ACP agent failed to deserialize a streamed response.'),
  );
}
```

**Flow:** at session start the bridge spawns the agent child and immediately installs the monitor on its stderr (:401) — every non-empty line is forwarded to `turn.bridgeLog` at warn level under subsystem `acp.agent.stderr`, and the sentinel check runs on the VT-stripped, lowercased text. runTurn captures the monitor promise BEFORE any prompt work and treats a missing monitor as a hard error ('did not start stderr monitoring' :146–152); the promise is raced alongside stream consumption, so a sentinel match rejects the turn even while the JSON-RPC pending request is still open. Stream end without sentinel never resolves the failure promise (it is `Promise<never>`); the async pump's own errors are routed to the same reject.
**Invariant:** observation never mutates the protocol — forwarding a line to the log has no side effects on the RPC channel; the sentinel is matched on normalized text (ANSI-stripped, case-folded) so colored/case-variant agent output cannot evade it; the failure path is a promise, not a callback, so it composes with Promise.race-based turn settlement; a turn can never start without a live monitor (the null check is fail-closed); partial lines are never evaluated — only complete lines (plus the final flush) reach the sentinel check.
**Probe:** `bridge/agent-stderr-monitor.test.ts` (25L, 1 case) — writes an ordinary diagnostic line then a VT-colored sentinel line through a PassThrough stream; pins BOTH the forwarding order (Nth calls with raw lines, ANSI codes intact) and the rejection with the exact 'ACP agent failed to deserialize a streamed response.' message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "monitorACPAgentStderr failed to deserialize ResponseStreamEvent stderr sentinel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stderr-sentinel pattern for any child process whose failure mode is "logs an error but keeps its request channel open": return the failure as a Promise<never> so callers race it into their existing settlement, normalize before matching (strip ANSI, case-fold) to survive cosmetic log changes, forward every line to structured logging in parallel, and fail-closed on "monitor not installed". Adapt the sentinel string to your agent's actual failure vocabulary (it is deliberately narrow — one known decoding failure — not a general error heuristic); omit the monitor where the child's RPC layer reliably rejects on failure. Coverage caveat: single-case test; the partial-line flush and pump-error branches are deterministic-read-only.
