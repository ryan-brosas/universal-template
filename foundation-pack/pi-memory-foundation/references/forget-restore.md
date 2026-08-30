<!-- capsule-v2 -->
# Forget & restore — block-aware deletion with durable recovery records and idempotent restore

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent delete memory entries as a first-class operation — removing whole stamped blocks, persisting a durable recovery record BEFORE mutating, and restoring idempotently?

## Forget & restore
**Path/Symbol:** `index.ts:forgetBlocks` (675–725), `recoveryPath` (727–730), `isRecoveryRecord` (732–745), `writeRecoveryRecord` (747–760), `readRecoveryRecord` (762–774).
**Signature:** `forgetBlocks(content, match): {content, removed: string[]}`; `writeRecoveryRecord(target, date, removedContent): RecoveryRecord`; `readRecoveryRecord(recoveryId): {record, filePath} | null`.
**Data Shape:** `MemoryTarget = "long_term" | "daily"`. `RecoveryRecord = { version: 1, id, createdAt, target, date?, removedContent: string[], restoredAt? }`. `RECOVERY_ID_REGEX` enforces UUIDv4. `MEMORY_ENTRY_META_COMMENT_REGEX` matches `<!-- ts [sid] -->` and `<!-- last updated: ts [sid] -->` and `<!-- HANDOFF ts [sid] -->` stamps.

### Decisive source
```ts
// forgetBlocks (675-725): split content into blocks; stamped entries are units,
// unstamped content falls back to blank-line paragraph blocks.
for (const line of normalizedContent.split("\n")) {
  if (MEMORY_ENTRY_META_COMMENT_REGEX.test(line)) {
    flushCurrent(); currentLines = [line]; currentIsStamped = true;
  } else { currentLines.push(line); }
}
// ... a block is removed iff block.toLowerCase().includes(needle)
if (removed.length === 0) return { content, removed };
const joined = kept.join("\n\n").trim();
return { content: joined ? `${joined}\n`.replace(/\n/g, newline) : "", removed: removed.map(b => b.replace(/\n/g, newline)) };

// writeRecoveryRecord (747-760): durable JSON, flag "wx" so a collision fails loudly
fs.writeFileSync(filePath, `${JSON.stringify(record, null, 2)}\n`, { encoding: "utf-8", flag: "wx" });
```

**Flow:** (1) `forgetBlocks` normalizes CRLF/BOM, segments content into stamped blocks (from one timestamp comment to the next) or blank-line paragraphs, and removes every block containing the case-insensitive `match`. (2) The memory_forget tool calls `writeRecoveryRecord` FIRST (persisting the complete removed payload) and only then writes the mutated file — a failed recovery write never yields an unrecoverable deletion. (3) `memory_restore` reads the record, appends only entries NOT already present (idempotent, so later writes survive), and stamps `restoredAt`.

**Invariant:** deletion is reversible: the full removed content is durably persisted under a UUIDv4 before the source is touched; restore appends only missing entries and never duplicates; a recovery record is only trusted after strict schema+UUID validation.

**Probe:** `test/unit.test.ts` — `forgetBlocks` describe (:2172): `removes the matching entry with its timestamp stamp` (:2183), `match is case-insensitive` (:2193), `removes multiple matching blocks` (:2198), `removes an entire stamped entry when a later paragraph matches` (:2204), `preserves CRLF entry boundaries` (:2223), `recognizes the first generated entry when the file starts with a UTF-8 BOM` (:2241), `no match leaves content untouched` (:2258), `removing the only entry empties the file` (:2268); `memory_forget tool` describe (:2275): `persists complete removed content and restores it by visible recovery ID` (:2364), `rejects invalid recovery IDs without reading outside the recovery directory` (:2358). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "forgetBlocks writeRecoveryRecord readRecoveryRecord isRecoveryRecord", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the block-aware forget (stamped units + blank-line paragraph fallback), the durable UUIDv4 recovery record written before mutation, the strict record validation, and the idempotent append-only restore. Adapt the timestamp-comment regex, the recovery directory, and the target names to the host. Omit nothing here — this is the portable forget/restore core.
