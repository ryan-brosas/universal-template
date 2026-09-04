<!-- capsule-v2 -->
# Settled-gate auto-resume — how does the loop restart itself without interrupting a busy agent?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** When and how is the "run next iteration" nudge delivered, and what stops it forever?

## pendingResume timer + isAgentSettled + MAX_AUTORESUME_TURNS=20
**Path/Symbol:** `extensions/pi-autoresearch/index.ts` — gates :511–523, settled check :457–459, schedule/send :461–505, ensure :548–565, lifecycle hooks :1051–1084.
**Signature:** `ensurePendingResume(pi, ctx, gate, composeMessage)`; gate variants: `shouldAutoResumeAfterTurn` = mode AND ran ≥1 experiment this session (STRICT), `shouldAutoResumeAfterCompact` = mode only (PERMISSIVE).
**Data Shape:** runtime fields `pendingResumeTimer` (setTimeout id) + `pendingResumeMessage`; `SETTLED_WINDOW_MS=800`; counter `autoResumeTurns` capped at 20.

### Decisive source
```ts
function sendPendingResumeIfReady(pi, ctx, runtime): void {
  const message = runtime.pendingResumeMessage;
  if (!message) return;
  if (!runtime.autoresearchMode) { cancelPendingResume(runtime); return; }  // turned off ⇒ cancel
  if (!isAgentSettled(ctx)) return;              // idle() && !hasPendingMessages() ⇒ wait (timer re-armed by caller)
  if (hasReachedAutoResumeLimit(runtime)) {
    cancelPendingResume(runtime);
    notifyAutoResumeLimitReached(ctx);           // one-shot user notification at 20 turns
    return;
  }
  cancelPendingResume(runtime);
  runtime.autoResumeTurns++;
  pi.sendUserMessage(message);                   // injects "Run the next iteration now. ..."
}
```

**Flow:** agent_end → if loop mode on AND ≥1 experiment ran this session → arm an 800ms timer carrying the resume message; timer fires → deliver ONLY if agent idle with no queued messages (otherwise leave armed — later events reschedule via `reschedulePendingResume`). Compaction event bypasses the ran-experiment requirement (compaction itself is evidence of a long-running loop) and uses the file-aware message variant. Mode off / limit 20 / new session (`agent_start` zeroes `experimentsThisSession`, pauses pending) each terminate the chain.
**Invariant:** the strict per-turn gate prevents infinite self-conversation when nothing productive happened (no run ⇒ no resume); the permissive compaction gate prevents the loop DYING just because context overflowed mid-experiment. The 800ms settle window debounces rapid agent_end bursts. Resume messages embed BENCHMARK_GUARDRAIL ("do not overfit to the benchmarks") every time — the anti-cheat instruction rides the same channel as the kick.
**Probe:** anchors: `grep -nE 'MAX_AUTORESUME_TURNS|SETTLED_WINDOW_MS' extensions/pi-autoresearch/index.ts | cut -d: -f1` → :58 (const 20), :59 (const 800), :494 (timer arm), :522 (limit fn), :526 (notify); `grep -n 'shouldAutoResumeAfterTurn\|shouldAutoResumeAfterCompact' extensions/pi-autoresearch/index.ts` → defs :512/:517 + calls :1077/:1083; regression test `__tests__/unit/regression.test.ts:25–104` pins the duplicate-activation guard that keeps re-issues from resetting `autoResumeTurns`.
**Retrieve:**
```bash
# BM25 noise-filter regression class (recurred 2026-08-24): multi-word queries on
# this small corpus can return total:0 even though symbols exist. The working
# primitive is search_code (line-exact, verified live):
codebase-memory-mcp cli search_code --project "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness" --pattern 'pendingResumeMessage'
# → 7 results incl. sendPendingResumeIfReady index.ts:461-482, schedulePendingResume :484-496, cancelPendingResume :452-455
```

## Verdict
Adopt the dual-gate + settle-window + hard-turn-cap design verbatim for any autonomous loop riding a host agent; adapt the transport (`sendUserMessage`) and limits; omit the compaction-specific message variant if your host lacks deterministic summaries. Direct tests cover the guard logic; the full async delivery path is source-pinned.
