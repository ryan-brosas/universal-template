<!-- capsule-v2 -->
# Config & paths — layered config loading with validation and agent-root/path normalization

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent load a layered JSON config over safe defaults — validating each field by type/enum, normalizing memory-dir paths, and deriving the overflow strategy — plus resolve the agent root and normalize project-memory paths safely?

## Config loader + path helpers
**Path/Symbol:** `src/config.ts:loadConfig` (73–171), `DEFAULT_CONFIG` (41–66); `src/paths.ts` — `resolveAgentRoot` (7–10), `expandHome` (12–18), `normalizeConfiguredMemoryDir` (20–27), `normalizeProjectsMemoryDir` (34–57), `resolveProjectsRoot` (59–62). `src/store/canonical-storage-path.ts:canonicalStoragePathSync` (14–50) for symlink-canonicalized storage identity.
**Signature:** `loadConfig(configPath = DEFAULT_CONFIG_PATH) → MemoryConfig`; `resolveAgentRoot(env?) → string`; `normalizeProjectsMemoryDir(input) → string | undefined`.
**Data Shape:** `MemoryConfig` defaults: `memoryMode: 'policy-only'`, `memoryOverflowStrategy: 'auto-consolidate'`, `reviewTransport: 'direct'`, `sessionSearch: { variant: 'legacy' }`, `correctionDetection: true`, `autoConsolidate: true`, `standingInstructionsEnabled: true`, plus char limits, nudge/flush intervals, and failure-injection bounds. Enums validated: `MEMORY_OVERFLOW_STRATEGIES`, `SESSION_SEARCH_VARIANTS`, `REVIEW_TRANSPORTS`, `THINKING_LEVELS`.

### Decisive source
```ts
// loadConfig (73-171): defaults-override merge with per-field validation
const config: MemoryConfig = { ...DEFAULT_CONFIG };
const isNonNegativeNumber = (v) => typeof v === "number" && Number.isFinite(v) && v >= 0;
const isStringArray = (v) => Array.isArray(v) && v.every(i => typeof i === "string");
if (parsed.memoryMode === "policy-only" || parsed.memoryMode === "legacy-inject") config.memoryMode = parsed.memoryMode;
if (isMemoryOverflowStrategy(parsed.memoryOverflowStrategy)) { config.memoryOverflowStrategy = parsed.memoryOverflowStrategy; hasMemoryOverflowStrategy = true; }
if (typeof parsed.autoConsolidate === "boolean") { config.autoConsolidate = parsed.autoConsolidate; hasLegacyAutoConsolidate = true; }
// ... per-field: char limits, nudge/flush, review transport, correction patterns, thinking level, session variant
if (hasMemoryOverflowStrategy) config.autoConsolidate = config.memoryOverflowStrategy === "auto-consolidate";
else if (hasLegacyAutoConsolidate) config.memoryOverflowStrategy = config.autoConsolidate ? "auto-consolidate" : "reject";
// memoryDir normalized via normalizeConfiguredMemoryDir; projectsMemoryDir via normalizeProjectsMemoryDir
// on parse error / missing file → return { ...DEFAULT_CONFIG }

// paths.ts
export function resolveAgentRoot(env = process.env) {
  const configured = env.PI_CODING_AGENT_DIR?.trim();
  return configured ? path.resolve(expandHome(configured)) : path.join(os.homedir(), ".pi", "agent");
}
export function normalizeProjectsMemoryDir(input) {
  // must resolve to a single safe relative segment under AGENT_ROOT (no "..", no abs escape)
  if (!isSafeRelativeDirectory(normalized)) return undefined;
  return normalized;
}
```

**Flow:** (1) `loadConfig` starts from `DEFAULT_CONFIG`, then overlays each user-provided field only when it passes its type/enum validation. (2) The overflow strategy and the legacy `autoConsolidate` flag are reconciled (strategy wins; else derive from the boolean). (3) `memoryDir`/`projectsMemoryDir` are normalized through the path helpers. (4) On a parse error or missing file, it falls back to defaults. (5) `resolveAgentRoot` honors `PI_CODING_AGENT_DIR` (with `~` expansion) else `~/.pi/agent`. (6) `normalizeProjectsMemoryDir` rejects any path that escapes the agent root or is not a single safe relative segment.

**Invariant:** invalid config values are silently ignored (defaults retained) rather than crashing; the overflow strategy and auto-consolidate flag never contradict; project-memory dirs are constrained to a safe single segment under the agent root; a corrupt/missing config file degrades to defaults.

**Probe:** `tests/config.test.ts` — validates the defaults-override merge, enum rejection, and the overflow-strategy/auto-consolidate reconciliation (on-disk; `tests/` excluded from the index by design). `tests/paths.test.ts` — `normalizeProjectsMemoryDir` rejects escaping/absolute paths. Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "loadConfig resolveAgentRoot normalizeProjectsMemoryDir canonicalStoragePathSync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the defaults-override merge with per-field type/enum validation, the overflow-strategy/auto-consolidate reconciliation, and the safe path normalization (agent root, single-segment project dir, symlink-canonicalized storage identity). Adapt the config keys, the enum vocabularies, and the default constants to the host. Omit the `PI_CODING_AGENT_DIR` env coupling and the `canonicalStoragePathSync` symlink resolution unless a target needs them.
