<!-- capsule-v2 -->
# Empty-summary compaction decline — returning undefined hands ownership back to the native summarizer

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When your compaction hook has nothing to contribute (no memory exists yet), do you return an empty replacement or decline — and what does each cost?

## Path/Symbol
**Path:** `src/hooks/compaction-hook.ts`
**Symbol:** `registerCompactionHook` empty-summary branch **:42-45**.

**Signature:** `pi.on("session_before_compact", handler) → { compaction } | { cancel: true } | undefined`

**Data Shape:** `renderSummary(projection.reflections, projection.observations) → string`; `summary.length === 0` exactly when no V3 memory exists (fresh sessions, V2-only ledgers, worker promises never settled).

### Decisive source
```ts
const summary = renderSummary(projection.reflections, projection.observations);
if (summary.length === 0) {
    // Decline ownership so Pi's native summarizer preserves the pre-cut context.
    return;   // undefined = "I don't own this compaction"
}
```

**Flow:** duplicate guard (`compactHookInFlight` → `{ cancel: true }`) → project the ledger → render summary → **empty ⇒ return undefined** (host falls back to its own LLM summarization over the FULL pre-cut context) → non-empty ⇒ replace with `{ compaction: { summary, firstKeptEntryId, tokensBefore, details } }`.

**Invariant:** An empty-string summary returned as a valid replacement would truncate context to NOTHING — the host would honor your "" as "summarize to zero". Declining instead preserves the user-visible behavior (native summarizer over full context) while keeping the extension honest about having nothing to say. Three distinct outcomes now exist and must not be conflated: `{ cancel: true }` (duplicate compaction in flight — refuse loudly), `undefined` (decline ownership — let native proceed), `{compaction}` (full replacement). The three renamed tests pin all three: fresh session / V2-only ledger / never-settled worker promises each expect `result === undefined` AND `resolveModel` never called.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -n "Decline ownership" src/hooks/compaction-hook.ts   # line 43 && \
grep -c "toBeUndefined()" tests/compaction-hook.test.ts    # expect 3 && \
npx vitest run tests/compaction-hook.test.ts               # 7 passed
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "registerCompactionHook renderSummary buildCompactionProjection", limit: 5 });
```

**Verdict:** Adopt the three-outcome contract (cancel vs decline-vs-replace). Adapt event names to your host. Omit nothing.
