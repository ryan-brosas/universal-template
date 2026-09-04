<!-- capsule-v2 -->
# Aho-Corasick LZ4 batch scan — how do you match thousands of patterns across thousands of files without decompression churn?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What buffer strategy lets one automaton scan compressed file contents at scale with zero per-file heap traffic?

## Thread-local reusable decompress buffer + bitmask results
**Path/Symbol:** `internal/cbm/ac.c:get_decomp_buf` (~250–267) + `cbm_ac_scan_lz4_batch` (298–360) + `cbm_ac_scan_bitmask` (ac.h:34).
**Signature:** `int cbm_ac_scan_lz4_batch(const CBMAutomaton *ac, const CBMLz4Entry *entries, int num_entries, CBMLz4Match *out_matches, int max_matches);`
**Data Shape:** Input entries {data, compressed_len, original_len}; output matches {file_index, pattern_bitmask} (uint64 ⇒ ≤64 patterns per automaton). Decompress buffer is thread-local, grown to the max original_len ONCE and reused; zero Go-heap allocation heritage.

### Decisive source
```c
// cbm_ac_scan_lz4_bitmask decompresses LZ4 data into a thread-local buffer
// and scans it through the AC automaton. Returns bitmask of matched patterns.
// Zero Go heap allocation — the decompression buffer lives in C.
...
// Allocate decompression buffer sized to the largest file.
int max_orig = 0;
for (int i = 0; i < num_entries; i++)
    if (entries[i].original_len > max_orig) max_orig = entries[i].original_len;
char *buf = get_decomp_buf(max_orig);
```

**Flow:** build automaton from pattern set → size TLS buffer to largest entry once → per entry: LZ4-decompress into the shared buffer → run AC over it OR-ing matched pattern ids into that file's bitmask → emit only files with nonzero masks.
**Invariant:** Buffer growth is monotone and per-thread — never realloc per file; failure to decompress skips silently (bitmask 0), never aborts the batch.
**Probe:** `tests/test_ac.c:ac_batch_scan` (4 names, ≥3 matches incl. overlapping "foo"+"bar" in "foobar"), `ac_scan_string` (bitmask 3 = both patterns), plus `tests/test_ac.c` table-bytes contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_ac_scan_batch", limit: 5 });
```

## Verdict
Adopt TLS-buffered batch scan for AC-over-compressed-corpus workloads; adapt the bitmask width or switch to id lists for >64 patterns; omit LZ4 if your corpus is plain text.
