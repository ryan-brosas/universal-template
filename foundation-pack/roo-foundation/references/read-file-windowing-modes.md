<!-- capsule-v2 -->
# read_file windowing modes — how does one tool expose line-slice reads AND semantic block reads without two tool names?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Where do slice vs indentation modes split, what are the exact defaults/bounds, and why does the truncation warning sit ABOVE the content?

## processTextFile — the mode fork inside read_file
**Path/Symbol:** `src/core/tools/ReadFileTool.ts:processTextFile` (269–330); constants `src/core/prompts/tools/native-tools/read_file.ts:6–12`; kernel `src/integrations/misc/indentation-reader.ts:readWithSlice` (434–469).
**Signature:** `private processTextFile(content: string, entry: InternalFileEntry): string`.
**Data Shape:** entry carries `{path, mode?: "slice"|"indentation", offset?, limit?, anchor_line?, max_levels?, include_siblings?, include_header?, max_lines?}`; output is a single string that is pushed as `File: <path>\n<result>`. Defaults: `DEFAULT_LINE_LIMIT=2000`, `MAX_LINE_LENGTH=2000`, `DEFAULT_MAX_LEVELS=0`.

### Decisive source
```ts
// Slice mode (default): simple offset/limit reading
// NOTE: read_file offset is 1-based externally; convert to 0-based for readWithSlice.
const offset1 = entry.offset ?? 1
const offset0 = Math.max(0, offset1 - 1)
const limit = entry.limit ?? DEFAULT_LINE_LIMIT
const result = readWithSlice(content, offset0, limit)
let output = result.content
if (result.wasTruncated) {
    const startLine = offset1
    const endLine = offset1 + result.returnedLines - 1
    const nextOffset = endLine + 1
    // Put truncation warning at TOP (before content) to match @ mention format
    output = `IMPORTANT: File content truncated.
	Status: Showing lines ${startLine}-${endLine} of ${result.totalLines} total lines.
	To read more: Use the read_file tool with offset=${nextOffset} and limit=${limit}.

	${result.content}`
} else if (result.returnedLines === 0) {
    output = "Note: File is empty"
}
```

**Flow:** execute → `isLegacyReadFileParams(params)`? legacy multi-file path : executeNew → rooignore gate → approval → stat (directory → "Use list_files tool instead") → `isBinaryFile`? binary ladder : buffer→utf8 (lossy U+FFFD, never throws) → processTextFile → nativeContent. Indentation branch defaults `anchorLine = anchor_line ?? offset ?? 1` and appends `Included ranges: s-e (total: N lines)` when not truncated.
**Invariant:** (1) offset is 1-based at the tool boundary and converted once (`offset1 - 1`) before hitting the kernel — double conversion is the classic wrong port. (2) The recovery recipe (`offset=${nextOffset} limit=${limit}`) is part of the contract: a model that cannot see the notice will not continue reading. (3) SWALLOW ASYMMETRY: `readWithSlice` returns out-of-bounds offsets as content `"Error: offset N is beyond file end (M lines)"` with `returnedLines: 0` — which this branch REPLACES with `"Note: File is empty"`; indentation-mode anchor errors survive verbatim because their branch keys off `includedRanges.length`, not returnedLines. A truly empty file renders as a single numbered blank line (`parseLines("")` → one record), so "File is empty" in practice means OUT-OF-BOUNDS OFFSET, not emptiness. (4) Lines longer than MAX_LINE_LENGTH are cut to `max-3` + `...` inside the formatter, so byte size per line is bounded independently of limit.
**Probe:** runner BLOCKED (no node_modules). Deterministic source pins, run from repo root: `grep -c 'convert to 0-based for readWithSlice' src/core/tools/ReadFileTool.ts` → 1; `grep -c 'Note: File is empty' src/core/tools/ReadFileTool.ts` → 1; `grep -c 'IMPORTANT: File content truncated' src/core/tools/ReadFileTool.ts` → 2 (both modes); kernel spec `src/integrations/misc/__tests__/indentation-reader.spec.ts:282–287` pins `readWithSlice(SIMPLE_CODE, 1000, 10)` → `returnedLines===0` + content contains "Error".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", qn_pattern: ".*ReadFileTool.*", file_pattern: "src/core/tools/ReadFileTool.ts", fields: ["lines"], format: "json", limit: 60 });
```

## Verdict
Adopt the dual-mode single-tool shape, the one-time 1-based→0-based conversion, top-placed self-describing truncation notices, and the errors-as-content result style. Adapt mode names/limits to your host. Omit VS Code-specific state plumbing. Caveat: tool-level spec mocks both kernels — cite the KERNEL spec for real behavior; document the "Note: File is empty" swallow explicitly if you keep it (it misreports out-of-bounds as emptiness).
