<!-- capsule-v2 -->
# Shared IO & session-attribution helpers — the two total functions every tool silently depends on

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** What are the exact failure semantics of memory-file reads and session-id attribution that all higher planes (context builder, snapshot, doctor, recovery, scratchpad) assume but never re-check?

## Shared IO & session-attribution helpers
**Path/Symbol:** `index.ts:shortSessionId` (:116–118), `readFileSafe` (:120–126). Direct tests: `test/unit.test.ts` `shortSessionId` describe (:357–373), `readFileSafe` describe (:375–400). Caller map (graph trace, pass 4): `readFileSafe` ← `buildMemoryContext`, memory_status `execute`, `getMemoryInventory`, `readRecoveryRecord`, `refreshMemorySnapshot` ×2; `shortSessionId` ← module-level stamp writers + memory_status `execute`.
**Signature:** `shortSessionId(sessionId: string): string`; `readFileSafe(filePath: string): string | null`.
**Data Shape:** `readFileSafe` returns full file text (`""` for an empty file is VALID and distinct from `null` = absent/unreadable). `shortSessionId` returns `sessionId.slice(0, 8)` — shorter inputs pass through unchanged, including `""`.

### Decisive source
```ts
export function shortSessionId(sessionId: string): string {
	return sessionId.slice(0, 8);
}

export function readFileSafe(filePath: string): string | null {
	try {
		return fs.readFileSync(filePath, "utf-8");
	} catch {
		return null;
	}
}
```

**Flow:** (1) Every read of an OPTIONAL file goes through `readFileSafe`; callers null-coalesce to a typed default — context builder skips the section, doctor counts zero, recovery reader reports unknown record, snapshot treats as empty. Because ENOENT and permission errors both collapse to `null`, no tool path can throw on a missing memory dir. (2) Writers stamp entries with `nowTimestamp()` plus `shortSessionId(...)` inside invisible comments (`<!-- ts … [abcdef12] -->`), attributing each note to a session while leaking at most 8 chars of the id into stored files. (3) The status doctor echoes the same short id back in its inventory.

**Invariant:** reads of optional files are TOTAL (missing → `null`, never throw); empty content must stay distinguishable from absence; attribution identifiers are bounded to 8 characters everywhere they touch disk.

**Probe:** EXECUTED pass 4 as part of the unit-suite run (`bun test test/unit.test.ts`): `returns null for non-existent file` (:385) and the four `shortSessionId` boundary cases (:358–372) green. Coverage check: `check_index_coverage(index.ts)` = `no_recorded_issue`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "readFileSafe shortSessionId", limit: 10, fields: ["signature", "name", "file"] });
```
Pass-4 retrieval: `search_graph` name_pattern `^(execute|flushCurrent|mark|shortSessionId|readFileSafe)$` with signature fields located both helpers; `trace_path(readFileSafe, inbound)` returned the six callers listed above; `get_code_snippet` excerpts matched the direct byte read of :114–127.

## Verdict
Adopt both contracts verbatim: total optional-file reads with explicit `null`, and 8-character session attribution in persisted stamps. Adapt the encoding (UTF-8) and id length to the host. Omit nothing — porting any memory plane without these two semantics reproduces crash-on-fresh-install and full-session-id-leak bugs.
