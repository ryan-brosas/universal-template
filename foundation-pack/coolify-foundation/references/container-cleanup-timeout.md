<!-- capsule-v2 -->
# Container cleanup timeout — how are stop/remove failures contained so cleanup never fails a good deployment?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** `docker rm` can hang on wedged daemons — how does Coolify bound it, detect the hang, and still guarantee eventual removal?

## graceful_shutdown_container / removeContainerWithTimeout / dockerStopCommand / dockerRemoveCommandWithTimeout
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:graceful_shutdown_container` (lines 3971–3989), `removeContainerWithTimeout` (3991–4019); helpers in `bootstrap/helpers/docker.php:dockerRemoveCommandWithTimeout` (line 267), `dockerStopCommand` (line 244).
**Signature:** `private function graceful_shutdown_container(string $containerName, bool $skipRemove = false)`, `private function removeContainerWithTimeout(string $containerName): void`, `function dockerRemoveCommandWithTimeout(string $container, int $timeout = 60, int $killAfter = 10): string`.
**Data Shape:** Marker constant `CONTAINER_REMOVE_TIMEOUT_MARKER = '__COOLIFY_CONTAINER_REMOVE_TIMEOUT__'`; grace period from `ApplicationSetting::deploymentStopGracePeriodSeconds()` (dev fallback MIN_STOP_GRACE_PERIOD_SECONDS).

### Decisive source
```php
$script = "if command -v timeout >/dev/null 2>&1; then output=\$(timeout -k {$killAfter}s {$timeout}s docker rm -f {$container} 2>&1); exit_code=\$?; else output=''; exit_code=124; fi; if [ \"\$exit_code\" -eq 124 ]; then echo '__COOLIFY_CONTAINER_REMOVE_TIMEOUT__'; elif ... grep -q 'No such container:'; then exit 0; ...";
```
and the job-side detection:
```php
$output = (string) $this->saved_outputs->get($outputKey, '');
if (! str_contains($output, self::CONTAINER_REMOVE_TIMEOUT_MARKER)) return;
$this->application_deployment_queue->addLogEntry(
    "Warning: Removing container {$containerName} timed out after 60 seconds. The deployment will continue and cleanup will be retried in 5 minutes.", 'stderr');
RemoveContainerJob::dispatch($this->server->id, $containerName)->delay(now()->addMinutes(5));
```

**Flow:** stop = `docker stop --timeout=<grace>` (flag spelled `--time=` for older Docker via dockerStopTimeoutOption) with ignore_errors + hidden → remove = shell-level `timeout -k 10s 60s docker rm -f`, exit 124 ⇒ echo marker; marker captured through `save:` key and inspected in PHP → dispatch delayed retry job. Every cleanup call site wraps errors so cleanup exceptions log as warnings and never re-throw when `newVersionIsHealthy || $force`.
**Invariant:** Idempotency — "No such container" is treated as success (exit 0). Cleanup failure NEVER fails an otherwise-successful deployment; the marker string crosses the process boundary inside command OUTPUT because the remote side has no channel back except stdout. The `handle()` finally-block gracefully shuts down the builder container (`skipRemove: true`) since it runs with `--rm`.
**Probe:** `grep -c "__COOLIFY_CONTAINER_REMOVE_TIMEOUT__" app/Jobs/ApplicationDeploymentJob.php bootstrap/helpers/docker.php` → 1 line each file (verified live: 2 files, 2 lines).
**Retrieve:** search_graph project ext-coolify query "graceful_shutdown_container removeContainerWithTimeout rolling_update" → Method nodes app/Jobs/ApplicationDeploymentJob.php 3971–4019.

## Verdict
Adopt bounded remove + output-marker handoff + delayed retry + never-fail-good-deploys cleanup policy; adapt RemoveContainerJob to your queue; omit Docker version flag-compat table if you control daemon versions.
