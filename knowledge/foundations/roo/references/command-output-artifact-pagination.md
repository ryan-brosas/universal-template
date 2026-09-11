<!-- capsule-v2 -->
# read_command_output artifacts — how do you give a model grep+pagination over a 100MB command log without loading it, and with no approval gate?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What makes it safe to hand an LLM byte-level read access to persisted command output outside the workspace?

## ReadCommandOutputTool — whitelist grammar + bounded byte windows
**Path/Symbol:** `src/core/tools/ReadCommandOutputTool.ts` (whole class 85–481; `isValidArtifactId` 215–220, `readArtifact` 236–272, `searchInArtifact` 294–394, `countNewlinesBeforeOffset` 454–480). Storage: `<globalStorage>/tasks/{taskId}/command-output/cmd-{executionId}.txt`, written by the OutputInterceptor when execute_command output exceeds its preview threshold.
**Signature:** `execute(params: {artifact_id: string, search?: string, offset?=0, limit?=DEFAULT_LIMIT=40*1024}, task, callbacks)`.
**Data Shape:** artifact ids are strict `cmd-\d+.txt`; pagination unit is BYTES; results are text blocks `[Command Output: <id>] / Total size: X | Showing bytes a-b | TRUNCATED|COMPLETE / "" / numbered lines`.

### Decisive source
```ts
private isValidArtifactId(artifactId: string): boolean {
    // Only allow alphanumeric, hyphens, underscores, and dots
    // Must match pattern cmd-{digits}.txt
    const validPattern = /^cmd-\d+\.txt$/
    return validPattern.test(artifactId)
}
```
```ts
const combined = partialLine + chunk
const lines = combined.split("\n")
// Last element may be incomplete (no trailing newline), save for next iteration
partialLine = lines.pop() ?? ""
for (const line of lines) {
    lineNumber++
    if (regex.test(line)) {
        const lineBytes = Buffer.byteLength(line, "utf8")
        if (totalMatchBytes + lineBytes > limit) { hitLimit = true; break }
        matches.push({ lineNumber, content: line })
        totalMatchBytes += lineBytes
    }
}
```

**Flow:** validate id grammar → resolve task dir → fs.access existence check with "verify the artifact_id from the command output message" hint → stat totalSize → reject offset ∉ [0,totalSize) → search mode (case-insensitive regex; invalid syntax escapes to literal via `/[.*+?^${}()|[\]\\]/g`) or read mode (positional `fileHandle.read(buffer, 0, min(limit, totalSize-offset), offset)`); start line for numbering = newlineCount-before-offset in 64KB chunks + 1; UI informed via say("tool", {readStart, readEnd, totalBytes, …}) — then result pushed directly.
**Invariant:** (1) The ID GRAMMAR IS THE ACCESS CONTROL: `/^cmd-\d+\.txt$/` admits no separators, so path traversal is impossible by construction and NO rooignore/approval gate exists on this tool — artifacts live OUTSIDE the workspace on purpose. (2) Memory is O(chunk) everywhere: reads allocate min(limit, remaining); search streams 64KB chunks carrying partialLine across boundaries; line-number reconstruction counts 0x0a bytes chunk-wise instead of allocating `offset`. (3) Search budget stops BEFORE adding the first match that would exceed the byte limit — matches.length is what "Showing first N" honestly reports, but when hitLimit fired there is NO more-matches marker (label says "Total matches" for collected-so-far; porters wanting true totals must re-scan). (4) Byte offsets can split UTF-8 sequences → replacement chars at window edges; line numbers after a mid-line offset refer to the next physical line. (5) consecutiveMistakeCount resets ONLY on the success path (line 194).
**Probe:** runner BLOCKED. Direct test exists (`__tests__/ReadCommandOutputTool.test.ts`) covering formatBytes/escape/window behaviors. Deterministic source pins from repo root: `grep -cF '/^cmd-\d+\.txt$/' src/core/tools/ReadCommandOutputTool.ts` → 1; `grep -cF 'partialLine = lines.pop() ?? ""' src/core/tools/ReadCommandOutputTool.ts` → 1; `grep -cF 'return newlineCount + 1' src/core/tools/ReadCommandOutputTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", qn_pattern: ".*ReadCommandOutputTool.*", fields: ["lines"], format: "json", limit: 40 });
```

## Verdict
Adopt whitelist-id + out-of-workspace storage as the pattern for ANY agent-readable execution artifact (it removes the approval round-trip safely); adopt chunked streaming with partial-line carry for log search. Adapt chunk sizes, default limit, and header copy. Omit nothing silently: dropping the pre-add byte-budget break turns bounded search into unbounded memory. Caveat: test file cited by name; runner unavailable at pin — behavior pinned via source reads + greps per lane precedent.
