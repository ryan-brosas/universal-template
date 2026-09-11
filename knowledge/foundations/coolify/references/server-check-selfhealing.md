<!-- capsule-v2 -->
# Server check & proxy self-healing — how does the periodic server job converge containers, sentinel, log drain, and proxy state?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** What does one server-check tick reconcile, and how do timeouts avoid poisoning Horizon's failed-job list?

## ServerCheckJob
**Path/Symbol:** `app/Jobs/ServerCheckJob.php` (lines 21–118; handle at 52–102, failed at 38–50).
**Signature:** `class ServerCheckJob implements ShouldBeEncrypted, ShouldQueue` — `public function middleware(): array`, `public function failed(?\Throwable $exception): void`, `public function handle()`.
**Data Shape:** `$tries = 1`, `$timeout = 60`; WithoutOverlapping key `server-check-<uuid>` expireAfter 60s dontRelease.

### Decisive source
```php
public function failed(?\Throwable $exception): void
{
    if ($exception instanceof TimeoutExceededException) {
        Log::warning('ServerCheckJob timed out', ...);
        $this->server->increment('unreachable_count');
        // Delete the queue job so it doesn't appear in Horizon's failed list.
        $this->job?->delete();
    }
}
...
if (! $foundProxyContainer) {
    $shouldStart = CheckProxy::run($this->server);
    if ($shouldStart) {
        StartProxy::run($this->server, async: false);
        $this->server->team?->notify(new ContainerRestarted('coolify-proxy', $this->server));
    }
} else {
    $this->server->proxy->status = data_get($foundProxyContainer, 'State.Status');
    $this->server->save();
    ConnectProxyToNetworksJob::dispatchSync($this->server);
}
```

**Flow:** skip when server unreachable/unusable or swarm-worker/build-server → fetch containers once → GetContainersStatus reconciles DB container rows → sentinel dispatched if enabled → log-drain container started/restarted if missing or not running → proxy: missing ⇒ CheckProxy/StartProxy + team notification; present ⇒ status mirrored to server model and network reconnection dispatched synchronously.
**Invariant:** The tick is CONVERGENT and idempotent — every substep checks current state before acting; timeouts are expected (60s cap) and treated as unreachability signal (unreachable_count++) rather than failures; encrypted queue payload because container metadata can embed sensitive env values. Proxy start is synchronous inside the job (async: false) so the next tick sees truth rather than racing itself.
**Probe:** `grep -c "unreachable_count" app/Jobs/ServerCheckJob.php` → 1 line; `grep -n "dontRelease" app/Jobs/ServerCheckJob.php app/Jobs/ScheduledJobManager.php` → exactly one line each (33 / 62, verified live).
**Retrieve:** search_graph project ext-coolify query "ServerCheckJob containers" → Class/Method nodes app/Jobs/ServerCheckJob.php.

## Verdict
Adopt convergent per-tick reconciliation + timeout-as-signal failure policy as portable watchdog design; adapt Horizon job deletion and Sentinel/log-drain specifics away; omit proxy vendor detection details beyond the pattern.
