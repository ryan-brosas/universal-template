<!-- capsule-v2 -->
# cron-watcher-debounce-escalate — how does an fs.watch front-end debounce save bursts without ever losing a deletion?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When a watcher feeds a disk→DB reconciler, how do you collapse editor save bursts while still tombstoning deleted specs whose single-path handler cannot see them?

## Trailing-edge per-path debounce; filter-before-schedule mirroring the walk skip set; delete ⇒ full-walk escalation; mkdir-before-watch lifecycle
**Path/Symbol:** `sdk/packages/core/src/cron/specs/cron-watcher.ts` (`CronWatcher` :26-102; `start` :39-60; `scheduleReconcile` :71-80; `reconcileNow` :82-101).
**Signature:** `new CronWatcher({reconciler, debounceMs?=250, onError?, onReconciled?})`; `start()/stop()/dispose(): void`.
**Data Shape:** `pending: Map<relativePath, timer>` — one trailing-edge timer per changed path; the class owns no state about file contents, only paths. `disposed` latch flips permanently.

### Decisive source
```ts
this.watcher = watch(dir, { recursive: true }, (_eventType, filename) => {
	if (!filename) return;
	const rel = String(filename).replace(/\\/g, "/");
	if (!rel.endsWith(".md")) return;
	if (rel.startsWith("reports/")) return;   // MIRRORS reconciler.walk's skip set
	this.scheduleReconcile(rel);
});
// ...
const abs = resolve(this.reconciler.getCronDir(), relativePath);
if (!existsSync(abs)) {
	// File was deleted — force a full reconcile to catch the
	// missing source and mark the spec removed.
	await this.reconciler.reconcileAll();   // NOT reconcileFile
	await this.onReconciled();
	return;
}
```

**Flow:** start ⇒ mkdirSync(recursive) BEFORE watch (test-pinned) ⇒ per-event filter (truthy filename → slash-normalize → `.md` → not `reports/`) ⇒ clear-and-rearm per-path timer (250ms default, `Math.max(0,…)` clamps junk) ⇒ fire: existsSync? no ⇒ `reconcileAll()`; yes ⇒ round-trip rel through resolve→relative "to defend against a watcher emitting an unexpected format" ⇒ `reconcileFile` ⇒ `onReconciled()` (the materialization hook — reconcile disk→DB and materialize DB→queued runs are deliberately separate steps composed here).
**Invariant:** The watcher can never request work the reconciler walk itself would refuse (identical skip set). A deletion is NEVER handled by the single-path path — reconcileFile returns silently `undefined` when readFileSync throws, so it cannot tombstone; only the full walk sees the missing path and marks the spec removed + cancels queued runs. Nothing throws after start: every async entry funnels to onError; start is idempotent, stop is restartable, dispose makes a later start THROW "CronWatcher disposed".
**Probe:** `grep -cF 'await this.reconciler.reconcileAll();' sdk/packages/core/src/cron/specs/cron-watcher.ts` → 1; `grep -cF 'if (rel.startsWith("reports/")) return;' …` → 1; `grep -cF 'if (this.disposed) throw new Error("CronWatcher disposed");' …` → 1. Direct suite `cron-watcher.test.ts` (2 cases, read whole): "materializes after a watched file reconcile" (drives private reconcileNow directly; pins one queued one-off run per reconcile via onReconciled→materializeAll) and "creates the cron directory before starting the watcher". Coverage caveat: the suite is THIN — no debounce-timing or deletion-escalation case; those invariants are source-read only.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.cron.specs.cron-watcher.CronWatcher" });
```

## Verdict
Adopt trailing-edge per-path debounce with a filter set that mirrors the downstream walk, delete-escalates-to-full-reconcile, mkdir-before-watch, and the dispose latch. Adapt the 250ms constant, the skip set, and the materialization hook signature. Omit Cline's reconciler internals (covered by `cron-reconciler-loop`). Coverage: source+test read whole at pin; MCP coverage check not runnable this session (transport unavailable) — recorded caveat.

