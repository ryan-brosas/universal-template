<!-- capsule-v2 -->
# Schedule self-healing supervisor — how does a cron-driven scheduler keep a 1-minute fetch loop and queue worker alive without systemd?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How are overlapping fetch runs prevented, stuck workers killed, and dead mutexes recovered when the only supervisor is `schedule:run` every minute?

## Console Kernel::schedule
**Path/Symbol:** `app/Console/Kernel.php:33` (`schedule`, 33–268).
**Signature:** `protected function schedule(Schedule $schedule)` — executed on EVERY `schedule:run` tick (and via web-cron route).
**Data Shape:** mutexes live in the Laravel cache (`fetch_mutex_name` cache key stores the fetch command's mutex name); process discovery = `ps aux | grep <md5 worker identifier>` via `Helper::getRunningProcesses` (Helper.php:1766-1793, identifier = `md5(app.key . salt)` :1758-1761 so co-hosted instances don't kill each other).

### Decisive source
```php
// app/Console/Kernel.php:127-151 — stuck-fetch killer + orphaned-mutex recovery
$mutex_name = \Cache::get('fetch_mutex_name') ?? '';
// If there is no cache mutex but there are running fetch commands it means
// the mutex had expired after FETCH_MAX_EXECUTION_TIME and the existing
// command(s) is running longer than that.
if (count($fetch_command_pids) > 0 && !\Cache::get($mutex_name)) {
    shell_exec('kill '.implode(' | kill ', $fetch_command_pids));   // kill long-running fetchers
} elseif (count($fetch_command_pids) == 0) {
    $ps_works = \Helper::getRunningProcesses('schedule:run');       // sanity: ps actually works
    if (count($ps_works)) {
        if (\Cache::has($mutex_name)) { \Cache::forget($mutex_name); } // force-remove stale mutex
    }
}
```
The registration itself (:154-190): `$schedule->command($fetch_command_name)->withoutOverlapping($expiresAt = 30 /* FETCH_MAX_EXECUTION_TIME minutes */)` — the comment chain (:112-125) explains Laravel's default withoutOverlapping mutex lives 24 h, hence explicit expiry + the cached mutex NAME (the mutex name is only derivable from inside schedule(), so it's stashed for the next tick's killer logic). Cadence switch maps `config('app.fetch_schedule')` constants 1/2/3/5/10/15/30/60 → cron expressions (:164-189).

**Queue-worker half (:195-267):** `queue:work` re-scheduled every minute with `withoutOverlapping()`; if MORE than one worker process is found, `\Helper::queueWorkerRestart()` (cache-flag graceful stop) + sleep(1) + hard `kill` of still-stuck pids; if ZERO found but schedule:run runs, its stale 24 h mutex is reconstructed via a skipped-command `mutexName()` trick and forgotten (:246-259). Early bail-outs: `isScheduleRun()` (:274-281) lets web-cron requests pass only when route is `system.cron`; `--no-interaction` argv flag skips daemonizing.
**Invariant:** every liveness decision is DOUBLE-GATED by "ps works" (`getRunningProcesses('schedule:run')` non-empty) before touching cache state — a broken `ps` must not nuke mutexes. Kill order is graceful-restart-flag first, SIGTERM second. The fetch command embeds `--identifier=<md5>` so `ps | grep` finds exactly this instance's workers.
**Probe:** `grep -c "withoutOverlapping" app/Console/Kernel.php` (= 9 — 6 call/def lines + 3 comment lines) and `grep -c "getRunningProcesses" app/Console/Kernel.php` (= 5).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "schedule fetch mutex", limit: 8, fields: ["signature","name","file"] });
```
(rank#1 resolves `Kernel.schedule app/Console/Kernel.php 33-268`.)

## Companion monitors
`FetchMonitor` (FetchMonitor.php:38-72): alerts once when `fetch_emails_last_successful_run` older than `fetch_schedule*60 + alert_fetch_period*60` seconds; recovery email when `alert_fetch_sent` was latched; Option keys act as edge-trigger memory. `SendMonitor` (SendMonitor.php:31-45): flags `send_emails_problem` option when ANY queued SendReplyToCustomer job has waited > CHECK_PERIOD (12 h) in the DB jobs table — LIKE-matcher on serialized payload displayName.
**Probe:** `grep -c "alert_fetch_sent" app/Console/Commands/FetchMonitor.php` (= 4).

## Verdict
Adopt expiresAt-bounded withoutOverlapping + cached-mutex-name + pid-scan killer + double-gated mutex GC as a portable self-healing scheduler; adapt `ps aux` scraping to your platform's process table; omit web-cron unless you need serverless deploys. Direct tests: none upstream.
