<!-- capsule-v2 -->
# Scheduled cron dedup — how do scheduled backups/tasks fire exactly once per cron window despite chunked polling?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** A scheduler polling every minute must not double-fire a job when the manager runs late, restarts, or races itself — what is the dedup algorithm?

## ScheduledJobManager + shouldRunCronNow
**Path/Symbol:** `app/Jobs/ScheduledJobManager.php:shouldDispatch` (lines 621–629), `isDueCandidateBeforeExpensiveChecks` (631–655), `middleware/clearStaleLockIfPresent` (52–92); helper `bootstrap/helpers/shared.php:shouldRunCronNow` (936–957).
**Signature:** `private function shouldDispatch(string $frequency, Server $server, string $dedupKey): bool`, `function shouldRunCronNow(string $frequency, string $timezone, ?string $dedupKey = null, ?Carbon $executionTime = null): bool`.
**Data Shape:** Frequency strings may be named aliases normalized via `VALID_CRON_STRINGS[$frequency] ?? $frequency`; per-item cache key like `scheduled-backup:<id>`; heartbeat key `scheduled-job-manager:heartbeat` (TTL 300s).

### Decisive source
```php
$cron = new Cron\CronExpression($frequency);
$executionTime = ($executionTime ?? Carbon::now())->copy()->setTimezone($timezone);
if ($dedupKey === null) return $cron->isDue($executionTime);
$previousDue = Carbon::instance($cron->getPreviousRunDate($executionTime, allowCurrentDate: true));
$lastDispatched = Cache::get($dedupKey);
$shouldFire = $lastDispatched === null
    ? $cron->isDue($executionTime)
    : $previousDue->gt(Carbon::parse($lastDispatched));
// Always write: seeds on first miss, refreshes on dispatch.
Cache::put($dedupKey, ($shouldFire ? $executionTime : $previousDue)->toIso8601String(), 2592000);
return $shouldFire;
```

**Flow:** one ScheduledJobManager runs per minute on the crons queue under WithoutOverlapping('scheduled-job-manager') (expireAfter 90s, dontRelease) with self-healing for TTL=-1 stale Redis overlap locks → execution time FROZEN at handle() start → enabled backups+tasks chunked by id (100/chunk) and evaluated INTERLEAVED so neither type starves the other → cheap cron-window precheck (`isDueCandidateBeforeExpensiveChecks`) filters before loading servers → survivors go through skip-reason gauntlet (database/server deleted ⇒ row deleted; server not functional; unpaid cloud subscription) → final shouldDispatch via shouldRunCronNow in the SERVER's timezone → dispatch DatabaseBackupJob/ScheduledTaskJob/VolumeBackupJob.
**Invariant:** Fire decision is `previousDue > lastDispatched`, NOT `isDue(now)` — this is catch-up-safe: a manager down at the exact minute still fires once afterward because previousDue advanced past the stored stamp. On miss it stores previousDue (seed) so the next poll inside the same window doesn't refire; on fire it stores executionTime. All comparisons happen against the frozen executionTime so chunk N+1 sees the same clock as chunk N. Timezone comes from server settings with app.timezone fallback. Heartbeat lets the UI detect a dead scheduler.
**Probe:** `grep -n "getPreviousRunDate" bootstrap/helpers/shared.php app/Jobs/ScheduledJobManager.php` → shared.php lines 932+945 and ScheduledJobManager.php line 636 (verified live); the decisive call sites are 945/636.
**Retrieve:** search_graph project ext-coolify query "ScheduledJobManager shouldDispatch cron dedup" → Method nodes incl. bootstrap/helpers/shared.php translate/validate_cron_expression neighbors.

## Verdict
Adopt frozen-clock + last-dispatch-stamp dedup and interleaved chunking as pure scheduling behavior; adapt CronExpression/Cache to your stack; omit cloud subscription gating and volume-backup recovery specifics.
