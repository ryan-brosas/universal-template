<!-- capsule-v2 -->
# astgrep rule-scan runner — how do you evaluate many structural patterns over many files through ONE external CLI without version drift or partial-trust results?

**Source:** pi-fovea MIT `main@5bd4e6f5c56190fb174245266464607b11f7a337`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A porter needs batch structural pattern matching over thousands of files via an external binary whose installed version may lack features — how does pi-fovea keep one-process-per-chunk throughput while never trusting a half-parsed result?

## Connected graph-selected seam
**Path/Symbol:** `src/core/astgrep.ts:materializeRuleFile/scanChunk/hasRuleScan/patternRunAll` (:328–403, :476–486); capability probes `hasAstGrepAsync` (:92–110).
**Signature:** `scanChunk(rulePath, files, cwd): Promise<ScanMatch[] | undefined>`; `materializeRuleFile(rules: readonly ScanRule[]): Promise<string>`; `hasRuleScan(): Promise<boolean>`.
**Data Shape:** `ScanRule {id, language, pattern, constraints?}`; matches stream as NDJSON `{text, range.start.line, file, metaVariables.single/multi, ruleId}`; `undefined` = chunk untrusted (spawn error, timeout, nonzero exit, any JSON parse failure).

### Decisive source
```ts
const accept = (line: string): void => {
  if (!line || parseFailed) return;
  try {
    const raw = JSON.parse(line) as RawScanMatch;
    if (!raw.ruleId || !raw.range?.start || typeof raw.file !== "string") {
      parseFailed = true;
      return;
    }
    matches.push({ ...fromRawMatch(raw), ruleId: raw.ruleId });
  } catch {
    parseFailed = true;
  }
};
...
child.on("close", (code) => {
  if (carry.trim()) accept(carry);
  finish(code === 0 && !timedOut && !parseFailed ? matches : undefined);
});
```

**Flow:** rules serialized to one temp YAML (`JSON.stringify(rules)` memoizes the materialization keyed by content) → `ast-grep scan --rule <path> --json=stream <files…>` spawned under the shared spawn gate → stdout streamed line-by-line with carry buffer; one malformed line poisons the whole chunk (`parseFailed`) → close resolves `matches` only on exit 0 ∧ no timeout ∧ no parse failure, else `undefined` → caller records an ExtractionFailure implicating every file in the chunk.
**Invariant:** A chunk result is all-or-nothing trusted: `undefined` never masquerades as "no matches". Capability probes (`--version`, `scan --help`) are sticky-success / 15s-TTL-failure / inflight-deduped per binary path, so an install mid-session self-heals without reloads and hot paths pay at most one probe.
**Probe:** `tests/extract.test.ts` ("extracts call sites with callee names", "extracts literals from code and config files") — end-to-end proof that pattern-rule scans return callee/text captures through this runner; run `pnpm vitest run tests/extract.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "scanChunk hasRuleScan materializeRuleFile patternRunAll", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the all-or-nothing chunk trust, poison-line streaming parse, sticky/TTL/inflight capability probing, and content-keyed rule-file memoization. Adapt the concrete CLI (`ast-grep scan --json=stream`), chunk size (`AST_GREP_CHUNK=160`, Windows 8k argv ceiling), and 16 MiB maxBuffer to your tool. Omit pi-specific spawn-gate wiring details beyond "bound child processes globally".
