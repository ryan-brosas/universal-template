<!-- capsule-v2 -->
# E2E battery architecture — how does an e2e suite degrade gracefully when an optional backend is missing, while keeping the developer's real data safe?

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How do you order and gate a mixed end-to-end battery — always-runnable scenarios first, model/backend-dependent scenarios second — with preflight checks, a restore envelope, skip accounting, and exit codes CI can trust?

## E2E battery architecture
**Path/Symbol:** `test/e2e.ts:main` (:558–648); config block (:32–45: `BACKUP_SUFFIX=".e2e-backup"`, `TIMEOUT_MS=120_000`, `PI_E2E_PROVIDER`/`PI_E2E_MODEL` pins); preflight `checkPi()`; gates `checkQmdAvailable()`/`checkQmdCollection("pi-memory")`; scenario fns `testExtensionLoads`, `testContextInjectionDirect` (:309–327), `testMemoryWriteAndRecall`, `testScratchpadCycle`, `testDailyLog`, `testMemorySearchGraceful`, qmd-gated `testMemorySearchWithQmd`/`testMemorySearchNoResultsWithQmd`/`testSelectiveInjection`/`testTagsInSearch`/`testHandoffSurvivesToNextSession` (:521–552).
**Signature:** `main(): Promise<void>` → `process.exit(failed > 0 ? 1 : 0)`; `backupFile(file)` / `restoreFile(file)` around the whole battery.
**Data Shape:** counters `{ passed, failed, skipped }` plus an `errors[]` list printed in the summary; three files enter the backup envelope: MEMORY.md, SCRATCHPAD.md, today's daily log.

### Decisive source
```ts
// main() ordering (558-648): gate → envelope → tiers → restore → exit code
const piAvailable = checkPi();
if (!piAvailable) { process.exit(1); }          // hard preflight: no pi, no e2e
backupFile(MEMORY_FILE); backupFile(SCRATCHPAD_FILE);
const dailyFile = path.join(DAILY_DIR, `${todayStr()}.md`);
backupFile(dailyFile);
try {
	await test("extension registers 4 tools", testExtensionLoads);      // tier 1: cheap
	// … scenarios 2–6 always run …
	const qmdAvailable = checkQmdAvailable();
	const qmdCollection = qmdAvailable && checkQmdCollection("pi-memory");
	if (qmdAvailable && qmdCollection) {
		// scenarios 7–11 need qmd + collection
	} else {
		skipped += 5;                                  // degrade, don't fail
	}
} finally {
	_clearUpdateTimer();                               // kill debounced background work
	restoreFile(MEMORY_FILE); restoreFile(SCRATCHPAD_FILE); restoreFile(dailyFile);
}
process.exit(failed > 0 ? 1 : 0);
```

**Flow:** (1) Hard preflight aborts when `pi` is unusable — everything downstream needs it. (2) The three user-facing memory files are backed up with a `.e2e-backup` suffix BEFORE any scenario runs. (3) Tier 1 runs six scenarios that only need files + tools (registration, direct-write injection recall, write+cross-session recall, scratchpad cycle, daily log, graceful no-qmd search). (4) Tier 2's five scenarios run only when qmd AND the collection exist; otherwise they are counted as `skipped` with a printed reason. (5) Injection assertions plant deterministic tokens directly in memory files (`Favorite color: purple`; `HANDOFF_<ts>` token) then require the real model's answer to contain them — with "Do NOT use any tools" prompts so the CONTEXT must carry the fact (`testHandoffSurvivesToNextSession`: token OR "migration"). (6) `finally` cancels the debounced update timer FIRST (so no background write lands after restore), then restores all three files. (7) Exit code reflects failures only — skips are legitimate.

**Invariant:** the developer's real memory must be byte-identical after the run (backup before anything mutates, restore in `finally`, timer cancelled before restore); missing OPTIONAL backends downgrade to skips, never failures; every failure is collected and printed at the end rather than aborting mid-battery.

**Probe:** Runner-blocked in this environment (needs `pi` CLI + API key): recorded per Gate-5 rules. Deterministic substitutes EXECUTED pass 4: `npx tsx --eval` not used; instead structural grep proof — `grep -c "backupFile\|restoreFile" test/e2e.ts` ≥ 8 sites, `grep -n "_clearUpdateTimer" test/e2e.ts` = finally site (:640), and CI truth from `.github/workflows/e2e.yml` (dispatch-only, `PI_E2E_MODEL=gpt-4o-mini` pinned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "main backupFile restoreFile checkPi testContextInjectionDirect", limit: 10, fields: ["signature", "name", "file"] });
```
Pass-4 retrieval: `get_code_snippet(pi-memory.test.e2e.main)` returned the battery verbatim; `get_code_snippet(pi-memory.test.e2e.testContextInjectionDirect)` / `(…testHandoffSurvivesToNextSession)` confirmed the token-planting pattern; citation census showed 8 of 11 scenarios previously uncited.

## Verdict
Adopt the tier order (cheap deterministic → backend-dependent), hard-preflight vs soft-skip distinction, whole-battery backup/restore envelope with timer cancellation inside `finally`, planted-token injection assertions with tool-forbidding prompts, and fail-count-only exit codes. Adapt file lists and preflight probes to the host's storage and backend. Omit nothing; pair with `live-cli-eval-isolation.md` (transport) and `e2e-inprocess-tool-harness.md` (tool-tier execution).
