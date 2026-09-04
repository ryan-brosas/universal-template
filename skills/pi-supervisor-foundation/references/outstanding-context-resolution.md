<!-- capsule-v2 -->
# Outstanding-context extraction with resolution detection — how do unresolved errors reach the judge, and how does a fixed error get marked RESOLVED?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which six signal classes become outstanding items, what priority tags order them, and when does [ERROR] downgrade to [RESOLVED]?

## extractOutstandingContext (`src/compaction/build-sections.ts`)
**Path/Symbol:** `src/compaction/build-sections.ts:extractOutstandingContext` (:97-250); regex constants :42-57; `priorityTag` (:65-74); `isTscResolved` (:86-95); final map :242-249.
**Signature:** `(blocks) => string[]` — scans only `blocks.slice(-25)` tail, dedups by exact item string, caps at 8 items.
**Data Shape:** Item prefixes: `[bash:exit N]`, `[tsc]`, `[tests]`, `[no matches] <Tool> "pattern"`, `[<toolName>]`, `[user]`. Priority tags: `[ERROR]` for tsc + non-zero bash exit + generic tool errors, `[WARN]` for tests failures + user blockers, `[INFO]` for empty grep/glob.

### Decisive source
```ts
const TSC_ERROR_RE = /error TS\d+:.+/;
const TEST_FAIL_RE = /(?:FAIL|✗|✘|×)\s|(\d+)\s+(?:failed|failure|failing)/i;
const EMPTY_RESULT_RE = /^(?:No matches? found\.?|No files? matched\.?|0 results?|No results?\.?)$/i;
const BASH_OUTPUT_SCAN_LIMIT = 8_000;   // errors live at the START of output
// tsc file from "[tsc] src/auth.ts(5,18): error TS2304: ..."
const m = item.match(/^\[tsc\]\s+(\S+)\((\d+,\d+)\)/);
// Resolution: an Edit/Write to the SAME file at a LATER tail position ⇒
return tagged.replace(/^\[(ERROR|WARN)\]/, '[RESOLVED]');
```
Blocker prose arm (:212-224): assistant/user lines matching BLOCKER_RE (fail/broken/cannot/still broken/crash...) qualify ONLY if ≥15 chars, not a bullet (`[-*+>]`), not starting `(`, and starting with a capital/quote/backtick — then clipped at a SENTENCE boundary via clipSentence (150).

**Flow:** walk last-25 blocks → six ordered arms per block (bash exit ≠0 → tsc-in-output → tests-in-output → empty grep/glob WITH pattern recovered from the preceding call → isError tool_result classified tsc/tests-before-generic → blocker prose) → dedupe → cap 8 → tag priorities → resolve pass marks tsc items whose file was edited AFTER the error position.
**Invariant:** (1) Classification ORDER matters: a tool_result containing tsc errors is tagged [tsc], never generic. (2) Resolution requires BOTH same-file AND later-position — an edit BEFORE the error never resolves it. (3) Only the FIRST 3 tsc lines per output count (noise cap). (4) Empty-search arm walks BACKWARD for the call to recover the pattern — the item is useless without it.
**Probe:** `tests/full-fidelity-snapshot.test.ts` `captures tool errors in outstanding context` (:172-197); regex pins at build-sections.ts :42-62; graph pin `search_graph query:"extractOutstandingContext priorityTag"` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractOutstandingContext TSC_ERROR_RE BLOCKER_RE priorityTag", limit: 8 });
```

## Verdict
Adopt the six-arm taxonomy, priority tags, cap-8/dedup discipline, and edit-after-error RESOLVED downgrade. Adapt regexes to your ecosystem's compiler/test output. Omit the [user] prose arm if your judge already sees raw user text.
