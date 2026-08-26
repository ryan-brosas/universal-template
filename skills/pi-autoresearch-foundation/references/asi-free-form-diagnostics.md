<!-- capsule-v2 -->
# ASI free-form diagnostics — how do you capture agent reasoning per run without a schema migration?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the shape of `asi`, where is it validated (nowhere?), and which three keys does the UI promote?

## Actionable Side Information — any key/value dict; compaction surfaces hyp/next/rollback
**Path/Symbol:** type `extensions/pi-autoresearch/src/types/index.ts:9–14` (`interface ASI { [key: string]: unknown }`) + ExperimentResult.asi :31; CLI parse `--asi '{"k":"v"}'` (`harness/cli.ts:416–424`); server stores only when non-empty :1295 + strips empty from JSONL :1368; compaction promotion `src/compaction/index.ts:200–213`.
**Signature:** `asi?: Record<string, unknown>`; render rule `typeof v === 'string' ? v : JSON.stringify(v)` truncated at 80 chars with `…` in log output.
**Data Shape:** conventions taught by the skill: `hypothesis`, `next_action_hint`, `rollback_reason`; anything else allowed.

### Decisive source
```ts
// types/index.ts — the whole validation story:
/**
 * Actionable Side Information (ASI) — free-form diagnostics per experiment run.
 * The agent decides what to record. Any key/value pair is valid.
 */
export interface ASI { [key: string]: unknown; }
// compaction/index.ts — exactly three keys are promoted to labeled columns:
formatAsiField(asi, 'hypothesis', 'hyp'),
formatAsiField(asi, 'next_action_hint', 'next'),
formatAsiField(asi, 'rollback_reason', 'rollback'),
```

**Flow:** agent calls log with optional `--asi` JSON → server rejects nothing (any object accepted) → stored verbatim on the result row and persisted to JSONL (key omitted entirely when empty/absent so the ledger stays clean) → run-log text renders each entry ≤80 chars → compaction summary extracts ONLY the three conventional keys into the run-line format `hyp:/next:/rollback:`; all other keys survive in the file but not the summary.
**Invariant:** zero-schema-by-design: adding a new diagnostic dimension never touches code. The three promoted names are a DISPLAY contract between skill prose and compaction formatter — renaming them breaks summary rendering silently (string-typed, no compile check). Empty-dict suppression keeps `{}` rows byte-identical to legacy rows without asi.
**Probe:** direct test support: `__tests__/unit/compaction.test.ts:36–124` asserts `hyp:`/`next:`/`rollback:` rendering from JSONL-authored rows; anchors `grep -c formatAsiField extensions/pi-autoresearch/src/compaction/index.ts` → 6 lines (:200–213 def+helper block: 3 promoted calls at :203/:204/:205, def :209, helper body refs); `grep -n "delete jsonlEntry.asi" harness/server.ts` → :1368.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "asi hypothesis next_action_hint rollback_reason formatAsiField", limit: 10 });
```

## Verdict
Adopt the free-form dict + display-promoted-conventions pattern for any agent-loop telemetry; adapt promoted keys to your domain; omit the 80-char truncation only if your surface wraps. Coverage caveat: server-side accept-any path untested directly; rendering is compaction-test-pinned.
