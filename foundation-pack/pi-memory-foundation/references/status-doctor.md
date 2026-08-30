<!-- capsule-v2 -->
# Memory status doctor — a health tool built from one inventory snapshot plus lazy probes

**Source:** pi-memory (MIT) `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`; Codebase Memory `pi-memory`. **Question:** How do you build the "why is search behaving oddly?" diagnostic tool for an agent memory system so it never throws and always reports both file state and search readiness?

## Memory status doctor
**Path/Symbol:** `index.ts:getMemoryInventory` (:1354–1382 — pass-2 citation sweep's largest UNCITED seam); `memory_status` tool (:2351–2430); probe chain `qmdAvailable || (await detectQmd())` → `checkCollection("pi-memory")` → `probeEmbeddings()`.
**Signature:** `getMemoryInventory(): { dir, longTermChars, scratchpadOpen, scratchpadTotal, dailyCount, latestDaily }`; `execute(_toolCallId, {}, _signal, _onUpdate, _ctx)` (no params).
**Data Shape:** `embeddings: "ready" | "missing" | "unknown" | "n/a"`; `details = { ...inv, qmd, collection, embeddings, snapshotMode, qmdUpdateMode }`; human block `# Memory status` with ✓/✗/⚠/? marks.

### Decisive source
```ts
// getMemoryInventory (1361-1372, 1388-1398): every read is failure-tolerant
const longTerm = readFileSafe(MEMORY_FILE) ?? "";
const items = parseScratchpad(readFileSafe(SCRATCHPAD_FILE) ?? "");
let dailyFiles: string[] = [];
try {
  dailyFiles = fs.readdirSync(DAILY_DIR).filter((f) => f.endsWith(".md")).sort();
} catch { dailyFiles = []; }
return {
  dir: MEMORY_DIR,
  longTermChars: longTerm.trim().length,          // trimmed length, not raw size
  scratchpadOpen: items.filter((i) => !i.done).length,
  dailyCount: dailyFiles.length,
  latestDaily: dailyFiles.length ? dailyFiles.at(-1).replace(/\.md$/, "") : null,
};

// doctor (2364-2370): lazy probes only as deep as availability allows
const qmdOk = qmdAvailable || (await detectQmd());
embeddings = collectionOk ? await probeEmbeddings() : "n/a";
```

**Flow:** (1) inventory reads each source defensively (`readFileSafe` null-coalesce, try/catch on readdir) so a missing dir yields zeros, never a throw. (2) The doctor lazily re-detects qmd, then checks the collection, then probes embeddings — each stage only if the previous succeeded. (3) `embeddings === "missing"` triggers the same self-heal as search: `ensureQmdEmbed()` background start with a "re-run to confirm" message. (4) Output is dual-formatted: human text block plus machine-readable `details`.

**Invariant:** diagnostics must be safe on a fresh install (no memory dir, no qmd) — every layer degrades to a count of zero or an `"n/a"` status instead of erroring; the doctor reports configuration it did not change and heals embeddings but nothing else.

**Probe:** `test/unit.test.ts` `memory_status tool` describe (:1308): `registers with correct name` (:1324), `reports file inventory and qmd-unavailable state without throwing` (:1329 — asserts text contains `"qmd available: ✗"` and `details.qmd === false`, `details.longTermChars > 0`). Coverage caveat: `getMemoryInventory`'s individual fields have no dedicated unit tests; they are exercised transitively through the status tool test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "getMemoryInventory probeEmbeddings checkCollection memory_status", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: one defensive inventory snapshot + staged lazy probes + dual human/machine output + self-heal on missing embeddings. Adapt field names, marks, and config keys to your host. Omit nothing — this is the portable doctor pattern.
