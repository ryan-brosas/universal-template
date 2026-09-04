<!-- capsule-v2 -->
# Consolidated fact scan — how do imports, calls, and string literals all come out of ONE pattern pass instead of three separate sweeps?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Per-fact extraction passes re-read every file once per fact family — how does pi-fovea collapse import/call/literal extraction into a single tagged ast-grep scan while keeping call-site wards?

## Connected graph-selected seam
**Path/Symbol:** `src/core/extract.ts:coreScanRules/coreFactsFromScan` (:508–560); ward table `CALL_WARDS/CALL_WARD_PATTERN` (:344–369).
**Signature:** `coreScanRules(files: string[]): ScanRule[]`; `coreFactsFromScan(files, cwd, source, matches): Promise<ScannedCoreFacts>`.
**Data Shape:** rules carry namespaced ids `fovea-core-import-<n>` / `fovea-core-call-<n>` / `fovea-core-literal-<n>`; the returned `ScannedCoreFacts` buckets matches by id prefix back into `{imports, calls, literals}`.

### Decisive source
```ts
for (const [language] of groupByLang(files)) {
  for (const pattern of IMPORT_PATTERNS[language] ?? []) add(CORE_IMPORT_PREFIX, language, pattern);
  for (const pattern of CALL_PATTERNS) {
    const metavar = pattern.startsWith("$O.") ? "M" : "F";
    add(CORE_CALL_PREFIX, language, pattern, { [metavar]: { not: { regex: CALL_WARD_PATTERN } } });
  }
  for (const pattern of STRING_PATTERNS[language] ?? []) add(CORE_LITERAL_PREFIX, language, pattern);
}
```

**Flow:** one rule document per language batch (imports + calls + literals together) → single consolidated scan per chunk → `coreFactsFromScan` partitions matches by `ruleId` prefix → imports/calls go through their match-shapers while literals additionally get the completion sweep (`completeLiterals`: config-file scalars + template-literal regex) and a `file|line|text` dedupe.
**Invariant:** Call wards (`log/test-entry` callee deny-list) are compiled INTO the rule as constraints (`{not: {regex}}`), not filtered afterwards — warded callees never become matches, so they cannot dilute downstream conductance tiers. Rule ids are the only bucketing key; prefixes must stay unique across families.
**Probe:** `tests/extract.test.ts` ("extracts imports across languages", "extracts call sites with callee names") — same fixture proves both families emerge from the shared pipeline; run `pnpm vitest run tests/extract.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "coreScanRules coreFactsFromScan CALL_WARD_PATTERN anonymousVariadics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prefix-tagged multi-family rule documents evaluated in one pass, constraint-native wards, and prefix-bucketed result partitioning. Adapt the pattern tables per language set and the id-prefix scheme to your runner. Omit the ast-grep YAML dialect specifics if your engine takes rules programmatically.
