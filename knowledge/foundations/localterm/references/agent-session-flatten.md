<!-- capsule-v2 -->
# Session transcript flattening — how does a stored pi session file become a human-readable run log?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you reconstruct per-run transcript views (including "as of that run") from an append-only JSONL session shared by multiple runs?

## Role-dispatched flatten with tool-call correlation and time truncation
**Path/Symbol:** `packages/server/src/agent-session-reader.ts:readAgentSession` (:35–190).
**Signature:** `readAgentSession(sessionFile: string, untilMs?: number): Promise<AgentSessionEntry[]>`.
**Data Shape:** Retention: ≤`AUTOMATION_SESSION_MAX_ENTRIES = 10_000` entries AND ≤16 MiB total, oldest-evicted via insertion-ordered Map; oversized lines (>2 MiB) skipped wholesale by the stream reader; missing file ⇒ [].

### Decisive source
```ts
if (
          untilMs !== undefined &&
          typeof event.timestamp === "string" &&
          Date.parse(event.timestamp) > untilMs
        ) {
          return;
        }
```
```ts
} else if (role === "toolResult") {
            ...
            const name =
              (typeof toolResultMessage?.toolName === "string" && toolResultMessage.toolName) ||
              toolCall?.name ||
              "tool";
```

**Flow:** bounded line stream → JSON parse → optional untilMs skip → role dispatch: user text/tool_result blocks; assistant text+thinking+tool_use/toolCall blocks; top-level `toolResult` role messages (the OpenAI-provider shape) — every tool result resolves name+input from its pendingToolCalls map entry then DELETES it. Compaction records become `{type:"compaction", summary, tokensBefore}` entries.
**Invariant:** TWO provider shapes must both resolve: Anthropic-style (`user` message carrying `tool_result` blocks keyed by tool_use_id) AND OpenAI-style (assistant `toolCall` blocks + separate `role:"toolResult"` messages keyed by toolCallId). `untilMs` is what makes thread-mode history views correct: each historical run's UI passes finishedAt so it shows the branch AS OF THAT RUN rather than the latest state. Correlated names survive even when the map missed (fallback chain toolName→pendingCall→"tool").
**Probe:** `packages/server/tests/agent-runner.test.ts` readAgentSession describe (:437–695): dual-shape pins at :454 (Anthropic shape incl. compaction entry) and :573 (OpenAI toolCall/toolResult shape); untilMs pin :628 (`truncates the transcript at untilMs so an older run sees the branch as it was then`); retention bounds pin :669.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "readAgentSession toolResult untilMs compaction", limit: 10 });
```

## Verdict
Adopt the dual-shape dispatch + id-correlation + time-truncation design for any append-only agent transcript; adapt retention constants. Directly tested across five suites covering both wire shapes, caps, and time travel.
