<!-- capsule-v2 -->
# Remote command lifecycle — how does one SSH command become logs, saved outputs, retries, and cancellation?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** What exact contract does `execute_remote_command([...])` give callers for output capture, secret redaction, and cancel checks?

## ExecuteRemoteCommand trait
**Path/Symbol:** `app/Traits/ExecuteRemoteCommand.php:execute_remote_command` (lines 61–152), `executeCommandWithProcess` (157–246), `redact_sensitive_info` (21–59).
**Signature:** `public function execute_remote_command(...$commands)` where each item is a string or array `{command|0, hidden, type, ignore_errors, append, command_hidden, skip_command_log, save}`.
**Data Shape:** Appends JSON entries to `ApplicationDeploymentQueue->logs`: `{command, output, type: stdout|stderr, timestamp UTC, hidden, batch: static::$batch_counter}`; captured stdout accumulates in `$this->saved_outputs` Collection of Stringables.

### Decisive source
```php
$this->application_deployment_queue->refresh();
if ($this->application_deployment_queue->status === ApplicationDeploymentStatus::CANCELLED_BY_USER->value) {
    throw new \RuntimeException('Deployment cancelled by user', 69420);
}
...
if (! $this->application_deployment_queue->logs) {
    $new_log_entry['order'] = 1;
} else {
    try {
        $previous_logs = json_decode($this->application_deployment_queue->logs, associative: true, flags: JSON_THROW_ON_ERROR);
    } catch (\JsonException $e) {
        // If existing logs are corrupted, start fresh
        $previous_logs = []; $new_log_entry['order'] = 1;
    }
    ...
}
...
$this->application_deployment_queue->logs = json_encode($previous_logs, flags: JSON_INVALID_UTF8_SUBSTITUTE);
```

**Flow:** per command: non-root servers get sudo transformation (`docker exec` prefix special-cased) → cancellation refresh check → retry loop (see ssh-retry-classification capsule) → process started with 1h idle timeout streaming a callback that trims output, sanitizes UTF-8, REDACTS values of env vars flagged `is_shown_once`, appends log entry with monotonically increasing `order` + batch id, saves the model, and stores trimmed output under `save:` key (append=true concatenates) → records `current_process_id` so UI can kill → nonzero exit throws DeploymentException unless `ignore_errors`; error output falls back to stdout when stderr empty.
**Invariant:** The whole logs column is rewritten as one JSON array per line of output — corruption resets order numbering rather than failing the deployment; redaction happens BEFORE persistence so secrets never reach the DB; `save` captures are keyed per-command and read back via `$this->saved_outputs->get(key)` (health-check status, git ls-remote sha). Batch counter is STATIC across jobs sharing the class — it sequences UI grouping only, not correctness.
**Probe:** `tests/Feature/ApplicationDeploymentControlVarFilteringTest.php` subclasses override execute_remote_command proving it's the single choke point; `grep -c "redact_sensitive_info" app/Traits/ExecuteRemoteCommand.php` → 6 lines incl. definition and both call sites in log-entry construction (verified live).
**Retrieve:** search_graph project ext-coolify query "execute_remote_command redact_sensitive_info save" → Method nodes at app/Traits/ExecuteRemoteCommand.php 61–152 / 21–59.

## Verdict
Adopt the command-spec shape, redaction-before-persist, ordered JSON log protocol, and save-key output capture; adapt Eloquent log storage (column rewrite per line does not scale elsewhere); omit Horizon process-id bookkeeping.
