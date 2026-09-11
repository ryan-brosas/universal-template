<!-- capsule-v2 -->
# Log-entry budget ladder — how do you store an unbounded agent transcript under fixed caps without corrupting the file schema?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Which cap fires first, and why does every truncation slice BELOW the limit by the marker length?

## Marker-aware string caps → per-entry tool caps → count-then-byte entry drop
**Path/Symbol:** `packages/server/src/agent-log-utils.ts` (whole: `truncate` :15–21, `truncateFindings`/`truncateLog`, `truncateToolInput`/`truncateToolResult`, `capLogEntries` :118–129).
**Signature:** `capLogEntries(entries: AgentLogEntry[]): AgentLogEntry[]`.
**Data Shape:** Caps (constants.ts): findings 8_000 chars; log 65_536; log entries 500; tool input 200; tool result 1_000; custom capture 65_536 bytes; markers `\n…[truncated]`, `\n…[log truncated]`, `…`, `…[truncated]`.

### Decisive source
```ts
// Slice below `max` by the marker length so the result (text + marker) fits
// the schema's `.max(max)` — otherwise the stored value exceeds the cap and
// the file fails to load next time.
return raw.length > max ? raw.slice(0, Math.max(0, max - marker.length)) + marker : raw;
```
```ts
let trimmed =
    entries.length > MAX_AUTOMATION_LOG_ENTRIES
      ? entries.slice(entries.length - MAX_AUTOMATION_LOG_ENTRIES)
      : entries;
  let total = trimmed.reduce((sum, entry) => sum + entrySize(entry), 0);
  while (total > MAX_AUTOMATION_LOG_LENGTH && trimmed.length > 1) {
    total -= entrySize(trimmed[0]);
    trimmed = trimmed.slice(1);
  }
```

**Flow:** findings/log strings truncate with marker-reserved slicing → per-run structured log entries capped by COUNT first (keep newest 500) then by TOTAL BYTES (drop oldest until ≤64k or a single entry remains — recent turns hold the final answer, so eviction is oldest-first) → tool inputs/results carry their own smaller caps.
**Invariant:** The marker-length reservation is the whole point: zod `.max()` on the stored schema would make an exactly-at-cap value WITH marker appended fail validation, and automation-store repair would then silently rewrite it next load. Byte accounting includes name+thinking text via `entrySize`, not just text. `while (... && trimmed.length > 1)` keeps at least one entry even when a single entry exceeds the byte cap alone.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`bounds noisy custom harness output before building the stored log` :303–320 — writes 2× cap of stdout; asserts `result.log).toHaveLength(MAX_AUTOMATION_LOG_LENGTH)` AND contains "log truncated", pinning marker-reservation end-to-end).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "capLogEntries truncateFindings MAX_AUTOMATION_LOG_LENGTH", limit: 10 });
```

## Verdict
Adopt marker-reserved truncation for any schema-capped stored string and newest-keeping count-then-byte eviction for entry lists; adapt constants. Directly tested through the overflow integration case.
