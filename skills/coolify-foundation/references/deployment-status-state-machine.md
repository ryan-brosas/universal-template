<!-- capsule-v2 -->
# Deployment status state machine — how do status transitions stay terminal-once and race-free against user cancels?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** How does a 5k-line job keep its DB status correct when the user cancels mid-command and multiple code paths try to finish/fail it?

## transitionToStatus + isInTerminalState + checkForCancellation
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:transitionToStatus` (lines 4885–4894), `isInTerminalState` (4900–4921), `checkForCancellation` (4872–4880), `failed` (5007–5056); enum `app/Enums/ApplicationDeploymentStatus.php`.
**Signature:** `private function transitionToStatus(ApplicationDeploymentStatus $status): void`, `private function isInTerminalState(): bool`, `public function failed(Throwable $exception): void`.
**Data Shape:** Status is a string-backed enum on `ApplicationDeploymentQueue`: QUEUED / IN_PROGRESS / FINISHED / FAILED / CANCELLED_BY_USER. Cancellation uses exception code `69420` as an in-band sentinel.

### Decisive source
```php
private function isInTerminalState(): bool
{
    $this->application_deployment_queue->refresh();

    if (... FINISHED ...) return true;
    if (... FAILED ...) return true;

    if ($this->application_deployment_queue->status === ApplicationDeploymentStatus::CANCELLED_BY_USER->value) {
        $this->application_deployment_queue->addLogEntry('Deployment cancelled by user, stopping execution.');
        throw new DeploymentException('Deployment cancelled by user', 69420);
    }
    return false;
}

private function transitionToStatus(ApplicationDeploymentStatus $status): void
{
    if ($this->isInTerminalState()) return;
    $this->updateDeploymentStatus($status);
    $this->handleStatusTransition($status);
    queue_next_deployment($this->application);
}
```

**Flow:** handle() refreshes the row and bails if pre-cancelled → sets IN_PROGRESS + `horizon_job_worker` hostname → every long phase calls `checkForCancellation()` (also enforced inside `execute_remote_command` before/after each command and during retry waits) → success path `post_deployment()` calls `completeDeployment()` FIRST (status FINISHED before side effects), then best-effort notifications → failure lands in `failed(Throwable)` which calls `failDeployment()` (FAILED via same guarded transition) then removes the new container unless error code 69420 (registry-push failure keeps the running version) or PR/consistent-name deployments.
**Invariant:** Terminal states are immutable — every transition re-reads (`refresh()`) before writing, so a cancel racing a finish cannot clobber FINISHED; the retry-exhaustion path in ExecuteRemoteCommand additionally does a conditional UPDATE `where status != FINISHED` at SQL level. Cancel is signaled purely by DB status polling — no process signals. Code 69420 doubles as "cancelled" AND "don't roll back the image"; porters must not treat it as generic failure cleanup.
**Probe:** `tests/Feature/ApplicationPreviewQueueAdvancementTest.php` pins cancelled-by-user transitions advancing the queue; `grep -c "69420" app/Jobs/ApplicationDeploymentJob.php app/Traits/ExecuteRemoteCommand.php` returns 4 + 3 lines respectively (verified live; sum the per-file lines — 7 total sentinel sites).
**Retrieve:** search_graph project ext-coolify query "ApplicationDeploymentJob transitionToStatus" → Method node at app/Jobs/ApplicationDeploymentJob.php 4885-4894.

## Verdict
Adopt refresh-guarded single-writer transitions, terminal-state immutability, drain-on-every-transition; adapt the sentinel-code mechanism to typed exceptions; omit Horizon-specific worker attribution.
