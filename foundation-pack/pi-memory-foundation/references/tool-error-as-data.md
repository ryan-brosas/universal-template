<!-- capsule-v2 -->
# Tool error-as-data — validation failures return isError text, never throw

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory`. **Question:** How should an agent-facing tool report invalid input and runtime failure so the calling LLM can read the mistake and retry instead of the host crashing?

## Tool error-as-data
**Path/Symbol:** `index.ts` — seven `isError: true` sites: `memory_read` bad date (:1993); `memory_forget` empty match (:2076) + bad date (:2087); `memory_restore` unknown recovery ID (:2169); `memory_search` qmd-missing (:2251), collection-setup-failed (:2271), search exception (:2343). Contrast set: scratchpad no-match (:1866), forget no-match (:2108), restore-already-restored (:2177) are PLAIN results.
**Signature:** `return { content: [{ type: "text", text }], isError?: true, details?: object }`.
**Data Shape:** every branch — including errors — carries a string `content[0].text` and usually a machine-readable `details` payload; nothing rejects.

### Decisive source
```ts
// memory_forget (2073-2079): validation failure as data
if (!params.match.trim()) {
  return { content: [{ type: "text", text: "Error: 'match' must not be empty." }],
           isError: true, details: {} };
}

// memory_forget (2106-2111): "nothing matched" is NOT an error — plain result
if (result.removed.length === 0) {
  return { content: [{ type: "text",
    text: `No entries matching "${params.match}" in ${filePath}.` }],
    details: { path: filePath, removed: 0 } };
}

// memory_search (2335-2345): even caught exceptions come back as text
catch (err) {
  return { content: [{ type: "text", text: `memory_search error: ${err instanceof Error ? err.message : String(err)}` }],
           isError: true, details: {} };
}
```

**Flow:** each tool validates params first (`match.trim()`, `isValidDailyDate`) → returns flagged error data; expected misses (no match found, already restored, empty file) stay UNflagged so the model treats them as normal outcomes; only genuine failures (bad input, broken environment, thrown exceptions) carry `isError`. The LLM sees actionable prose ("Use YYYY-MM-DD", install instructions) either way.

**Invariant:** tools never throw across the extension boundary — the host never crashes on tool misuse, and the severity signal is a flag on returned data rather than control flow. The flag taxonomy is deliberate: user-input faults and environment faults get `isError`, semantic non-events do not.

**Probe:** `test/unit.test.ts` — `memory_read tool`: `read daily when file does not exist` (:1129) vs date-validation path pinned at source :1988-1996; `memory_forget tool`: `rejects empty match and bad dates` (:2340), `reports no match without touching the file` (:2305), `rejects invalid recovery IDs without reading outside the recovery directory` (:2358). Coverage caveat: `details.isError` itself has no dedicated assertion upstream; the flag sites are source-pinned at the seven line numbers above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "isError registerTool execute content details", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the contract: validate-then-return-data, reserve `isError` for input/environment faults, keep expected misses plain, always include human-readable guidance plus `details`. Adapt message wording to your host's tool schema. Omit nothing — this is the portable error-as-data pattern.
