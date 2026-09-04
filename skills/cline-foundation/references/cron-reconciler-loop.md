<!-- capsule-v2 -->
# cron-reconciler-loop — how does a scheduler treat the filesystem as startup truth and keep DB schedule state (including tombstones and next-run math) consistent with it?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should file-backed task specs reconcile into a DB store at startup and on watcher events — including removal, queued-run cancellation, and next_run_at computation that catches up exactly once?

## Scan-upsert-tombstone-refresh; reset-only-on-meaningful-change; catch-up base max(now,lastRun)
**Path/Symbol:** `sdk/packages/core/src/cron/specs/cron-reconciler.ts` (`walk` :53-80, `reconcileAll` :104-142, `reconcileFile` :149-193, `handleFileDeleted` :199-202, `refreshScheduleNextRunAt` :209-218, `applyScheduleNextRunAt` :220-240).
**Signature:** `reconcileAll(): Promise<ReconcileSummary{scanned, upserted, invalidParses, removed, changes}>`; `reconcileFile(relativePath, absolutePath): Promise<ReconcileChange | undefined>`; `handleFileDeleted(spec): void`.
**Data Shape:** Specs live as `.md` files under `~/.cline/cron` (workspace scope optional via ResolveCronSpecsDirOptions); store rows keyed by specId with sourcePath, sourceHash+mtimeMs, parseStatus valid|invalid, enabled, triggerKind one-off|schedule, scheduleExpr/timezone/nextRunAt/lastRunAt. UpsertSpecResult.record returns post-upsert state driving next-run logic. Coverage caveat: index reports parse_partial at line 60 only (`let entries: import("node:fs").Dirent[];`) — verified by direct read; walk logic fully present in source.

### Decisive source
```ts
// Startup contract: 'This is the startup source of truth: watcher events are
// triggers to re-run reconciliation for one file, not a replacement.'
const files = walk(this.cronDir);            // stack walk: .md only, skip reports/ subdir, per-dir try/catch
const seenPaths = new Set<string>();
for (const abs of files) { const rel = toPosixRelative(this.cronDir, abs); seenPaths.add(rel); ... }
const existing = this.store.listSpecs({ includeRemoved: false, limit: 10_000 });
for (const spec of existing) if (!seenPaths.has(spec.sourcePath)) this.handleFileDeleted(spec);   // tombstone + cancelQueuedRunsForSpec
this.refreshScheduleNextRunAt();

// next_run_at: compute only when missing or when meaning changed:
this.applyScheduleNextRunAt(result.record, {
	forceReset: !existing || existing.removed || !existing.enabled ||
		existing.scheduleExpr !== result.record.scheduleExpr || existing.timezone !== result.record.timezone });
// Catch-up policy 'one overdue catch-up on startup then advance to next slot':
const base = spec.lastRunAt ? Math.max(now, new Date(spec.lastRunAt).getTime()) : now;
const nextMs = getNextCronTime(spec.scheduleExpr, base, spec.timezone);
// invalid cron pattern: leave next_run_at as is; parse_status already reflects correctness
```

**Flow:** startup/watch → reconcileAll walks dir → per-file read+parse+upsert (invalid parses are RECORDED, never fatal to the scan) → valid enabled schedules get next_run_at computed iff missing/reset-forced → unseen DB paths tombstoned (markSpecRemoved) with their queued runs cancelled → final refresh pass over all enabled valid schedules | watcher path reuses reconcileFile for ONE file — full scan stays the authority.
**Invariant:** Disk presence is existence: anything in the DB without a seen sourcePath is removed=1 and loses its queued runs. Invalid specs persist with parseStatus=invalid instead of aborting reconciliation. next_run_at is stable under no-op rescans (only meaningful deltas force reset) and overdue schedules fire once then advance from max(now,lastRunAt) — never re-fire per elapsed slot.
**Probe:** `grep -cF 'seenPaths.add(rel);' …cron-reconciler.ts` → 1; `grep -cF 'this.store.cancelQueuedRunsForSpec(spec.specId);' …` → 1; `grep -cF 'Math.max(now, new Date(spec.lastRunAt).getTime())' …` → 1; `grep -cF 'if (entry.name === "reports") continue;' …` → 1; test pins (cron-reconciler.test.ts): "imports valid one-off and schedule specs on startup", "records invalid specs without failing the whole scan", "marks specs as removed when source files disappear", "cancels queued runs when spec is removed", "preserves overdue schedule next_run_at on startup refresh" — all present. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.cron.specs.cron-reconciler.CronReconciler.reconcileAll" });
// observed: Method lines 104-142 verbatim; coverage_note flags partial@60-60 (type annotation, verified by direct read)
```

## Verdict
Adopt scan→upsert→tombstone→refresh as THE startup reconciliation shape, watcher-events-as-triggers-not-replacement, record-don't-abort invalid parses, reset-next-run only on absent/removed/disabled/expr/tz deltas, and the single-catch-up base rule. Adapt spec format (.md front-matter here), storage backend, and cron evaluation. Omit Cline's SQLite store specifics. Runner-BLOCKED here; probes green.
