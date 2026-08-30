<!-- capsule-v2 -->
# Turn-settling hardening — how does a turn-based adapter survive child death, cancel-during-dispose, and a slow abort RPC?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How must the pending-turn state machine settle EVERY in-flight prompt (process exit, dispose race, cancel) so the ACP client never hangs, and where must cancellation NOT wait?

## Process-exit settling + cancel ordering + usage/error metadata
**Path/Symbol:** `src/acp/session.ts` (`handleProcessExit` :640-651, `dispose()` in-flight settle :418-427, `cancel()` reordering :509-514, `lastError` capture :617-626) + `src/acp/agent.ts` (`cancel()` non-blocking :1093-1100, `collectTurnUsage` :1101-1110) + `src/acp/usage.ts` whole (`sessionStatsToAcpUsage`, `withTimeout`).
**Signature:** `private handleProcessExit(code: number | null, signal: string | null): void`; `async collectTurnUsage(session: PiAcpSession): Promise<Usage | null>`; `sessionStatsToAcpUsage(stats: unknown): Usage | null`.
**Data Shape:** `touchedFilePaths: ReadonlySet<string>` accumulated per file-mutation tool call; `lastError: string | null = message + '\nstderr:\n' + stderrTailLines(8)`; usage = cumulative `{totalTokens, inputTokens, outputTokens, cachedReadTokens?, cachedWriteTokens?, _meta.piAcp.cost?}` or null.

### Decisive source
```ts
// ACP cancel is a notification; never block message dispatch on pi's abort RPC
// (which can be slow when pi is mid-turn). Queue clearing is synchronous inside
// session.cancel(); the rest runs in the background (F-018).
void session.cancel().catch(e => { process.stderr.write(...) })

// ...and inside session.cancel(), bridge calls die BEFORE the slow abort:
this.bridge?.cancelAll()          // was AFTER proc.abort() — the fix
await this.proc.abort()
```

**Flow:** `PiRpcProcess.onExit` handlers now reach the session: if a turn is pending on child death → set `lastError` from exit code/signal + 8-line stderr tail, flush enqueued updates, resolve with `'cancelled' | 'error'` — the request NEVER hangs on a dead child. `dispose()` mirrors this for an in-flight turn (flushEmits then `resolve('cancelled')`) after rejecting queued turns. Prompt-return path gains: post-turn `getSessionStats` raced under `withTimeout(…, 2_500)` mapped through `sessionStatsToAcpUsage` (returns null when no usable numbers so the field is OMITTED not zero-filled); `'error'` results carry `_meta.piAcp.error` (was: silently mapped to end_turn); end_turn runs the IDE gates then clears `touchedFilePaths`.
**Invariant:** every pendingTurn has exactly ONE settlement path that wins (exit handler vs agent_settled vs prompt-reject) because each sets `pendingTurn = null` before resolving; cancel notification dispatch is never awaited against a slow RPC; usage/errors ride `_meta` extensions rather than new wire fields.
**Probe:** `npx tsx --test test/unit/session-usage.test.ts test/unit/pi-rpc-process.test.ts` (usage mapping matrix incl. NaN/null shapes; transport exit semantics) — executed GREEN at pin; no dedicated `turn-lifecycle` suite exists in this repo — cancel/settle behavior is covered by these two suites plus pass-2 battery execution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "handleProcessExit collectTurnUsage cancelAll abort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exit-settles-prompt, bridge-cancel-before-abort ordering, timeout-raced best-effort usage collection, and error-via-_meta. Adapt the stats RPC name and Usage field mapping to your protocol. Omit cost passthrough unless your backend prices tokens. Direct tests executed green at the pin.
