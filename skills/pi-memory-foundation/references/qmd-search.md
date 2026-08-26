<!-- capsule-v2 -->
# qmd search — keyword/semantic/deep modes, result shaping, embedding self-heal, limit clamping

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent run qmd searches across memory files in three modes, shape the results, clamp the limit, and self-heal when embeddings are missing?

## qmd search
**Path/Symbol:** `index.ts:getQmdResultPath` (1255–1257), `getQmdResultText` (1259–1261), `runQmdSearch` (1291–1325), `probeEmbeddings` (1334–1351), `clampSearchLimit` (1239–1242), `searchRelevantMemories` (1193–1235), `getQmdSearchTimeoutMs` (964–967).
**Signature:** `runQmdSearch(mode: "keyword"|"semantic"|"deep", query, limit): Promise<{results, stderr}>`; `clampSearchLimit(value?, fallback=5, max=25): number`; `searchRelevantMemories(prompt): Promise<string>`; `probeEmbeddings(): Promise<"ready"|"missing"|"unknown">`.
**Data Shape:** `QmdSearchResult = { path?, file?, score?, content?, chunk?, snippet?, title?, [key] }`. Mode→subcommand: keyword→`search`, semantic→`vsearch`, deep→`query`. Args: `[subcommand, "--json", "-c", "pi-memory", "-n", limit, query]`. Default search timeout 60s.

### Decisive source
```ts
// runQmdSearch (1291-1325): mode → subcommand, then parse tolerant of shapes
const subcommand = mode === "keyword" ? "search" : mode === "semantic" ? "vsearch" : "query";
const args = [subcommand, "--json", "-c", "pi-memory", "-n", String(limit), query];
// ... on err, detect timeout via err.killed and add a hint
const results = Array.isArray(parsed) ? parsed : ((parsed as any).results ?? (parsed as any).hits ?? []);

// clampSearchLimit (1239-1242): the limit reaches `qmd -n`; guard NaN/0/negative/huge
if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
return Math.min(max, Math.max(1, Math.floor(value)));

// searchRelevantMemories (1193-1235): sanitize prompt, race against 3s timeout
const sanitized = prompt.replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, 200);
const results = await Promise.race([runQmdSearch("keyword", sanitized, 3),
  new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error("timeout")), 3_000); })]);
```

**Flow:** (1) `runQmdSearch` maps mode→subcommand, invokes via the swappable `execFileFn`, and parses the JSON tolerantly (array, `.results`, or `.hits`). (2) `clampSearchLimit` guards the `-n` argument. (3) `searchRelevantMemories` sanitizes the prompt (strip control chars, cap 200), checks the collection, races a keyword search against a 3s timeout, and formats snippets with `_path_` markers. (4) The memory_search tool detects a `need embeddings` stderr and kicks off `ensureQmdEmbed()` as self-heal.

**Invariant:** the `-n` limit is always a finite integer in `[1, max]`; search never blocks longer than its race timeout; a missing-embedding warning triggers an automatic background embed instead of a hard failure.

**Probe:** `test/unit.test.ts` — `clampSearchLimit` describe (:2154): `defaults when undefined or NaN` (:2155), `clamps to the valid range and floors fractions` (:2160); `memory_search tool` describe (:1263): `defaults mode to keyword and limit to 5` (:1299); `getQmdSearchTimeoutMs` describe (:1254): `accepts positive integer milliseconds and defaults invalid values` (:1255); pass-4 addition — `runQmdSearch qmd diagnostics` describe, `uses the configured qmd search timeout in execution and diagnostics` (:1226–1243): sets `PI_MEMORY_QMD_SEARCH_TIMEOUT_MS=90000`, captures `opts.timeout === 90_000` at the fake exec boundary AND asserts the rejection message contains `qmd timed out after 90s` — proving the env knob reaches BOTH the spawn options and the human hint (`index.ts:1305–1309`: `err.killed === true` → `qmd timed out after ${timeoutMs / 1000}s … retry shortly`). Tests are graph-resident in the FULL index (the earlier "tests excluded by design" caveat is obsolete).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "runQmdSearch clampSearchLimit searchRelevantMemories probeEmbeddings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mode→subcommand map, the tolerant result-shape parsing, the `clampSearchLimit` guard, the sanitized+raced auto-retrieval, and the embedding self-heal. Adapt the collection name, timeouts, and result-formatting to the host. Omit the qmd vendor's search internals unless a target needs them.
