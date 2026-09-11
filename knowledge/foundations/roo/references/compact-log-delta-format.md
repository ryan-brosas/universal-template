<!-- capsule-v2 -->
# CompactLogger/CompactTransport — what does a "compact" log line contain and why are timestamps deltas?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the on-disk log format, and which metadata-merge rules must a child logger preserve?

## Delta-timestamp NDJSON with parent-meta inheritance
**Path/Symbol:** `src/utils/logging/CompactLogger.ts:CompactLogger` (lines 12–150; `child` :76, `combineMeta` :118, entry build :139) + `src/utils/logging/CompactTransport.ts:CompactTransport` (:36–122; `write` :85, `ensureInitialized` :60).
**Signature:** `new CompactLogger(transport?, parentMeta?)`; `logger.child(meta): ILogger`; `transport.write(entry: CompactLogEntry)` where `CompactLogEntry = { t: number(delta ms), l: LogLevel, m: string, c?: ctx, d?: data }`.
**Data Shape:** one JSON object per line (NDJSON); `d` = meta minus `ctx`, omitted entirely when empty (`({ ctx: _, ...rest }) => Object.keys(rest).length > 0 ? rest : undefined`).

### Decisive source
```ts
write(entry: CompactLogEntry): void {
    const deltaT = entry.t - this.lastTimestamp
    this.lastTimestamp = entry.t
    const compact = { ...entry, t: deltaT }
…
// ensureInitialized(): mkdirSync(dirname) then writeFileSync(path, "", {flag:"w"})
//   followed by session-start marker {t:0,l:"info",m:"Log session started",d:{timestamp: ISO}}
```

**Flow:** level methods → combineMeta (parent spread UNDER call-site meta, but `ctx: meta.ctx || parentMeta.ctx` — an EMPTY-string call ctx falls back to parent) → entry built with absolute epoch `t` → transport converts to delta-vs-previous-entry. File output lazily initialized on FIRST write (mkdir recursive + truncate + session-start marker); every subsequent write appends via `{flag:"a"}` sync writes to BOTH stdout (level-gated by `LOG_LEVELS.indexOf` ordering) and file (ungated once filePath configured). `error/fatal` accept Error objects and expand them into `d.error = {name, message, stack}` with `ctx` defaulting to the LEVEL name.
**Invariant:** FILE WRITES IGNORE the level gate — config.level filters console only, so a file-configured transport always records everything it receives; truncation happens at init only (session marker t:0 anchors the delta timeline; absolute wall time survives solely in that marker's `d.timestamp`). Child loggers share ONE transport instance; close() emits a "Log session ended" marker whose `t` is delta-since-last-entry.
**Probe:** `grep -c 'deltaT' src/utils/logging/CompactTransport.ts` → 2; `grep -c 'flag: "a"' src/utils/logging/CompactTransport.ts` → 2 (append for entries + session-end); `grep -c 'ctx: meta.ctx || this.parentMeta.ctx' src/utils/logging/CompactLogger.ts` → 1; `grep -cF 'Log session started' src/utils/logging/CompactTransport.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CompactLogger CompactTransport", limit: 10 });
```
(caveat: BM25 returned zero hits for these class tokens at pin — doc-shaped plane; use search_code/grep as the retrieval primitive).

## Verdict
Adopt the delta-timestamp NDJSON format and lazy-init-with-session-marker lifecycle for any high-frequency agent logging. Adapt sink backends (sync appendFileSync is fine for extension hosts, not servers). Direct tests: `src/utils/logging/__tests__/CompactTransport.spec.ts` (File Handling :58, FS edge cases :123, "Delta Timestamp Conversion" :177) + `CompactLogger.spec.ts` with `MockTransport.ts`.
