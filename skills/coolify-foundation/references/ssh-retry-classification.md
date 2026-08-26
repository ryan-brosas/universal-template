<!-- capsule-v2 -->
# SSH retry classification — which SSH errors retry with backoff, and which fail immediately?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** A porter must not retry non-transport failures (a failing build command would re-run) — what exactly is the retryable set and the backoff formula?

## SshRetryable trait + ExecuteRemoteCommand retry loop
**Path/Symbol:** `app/Traits/SshRetryable.php:isRetryableSshError` (lines 12–54), `calculateRetryDelay` (59–68), `executeWithSshRetry` (78–132); consumer `app/Traits/ExecuteRemoteCommand.php:105–150`.
**Signature:** `protected function isRetryableSshError(string $errorOutput): bool`, `protected function calculateRetryDelay(int $attempt): int`, `protected function executeWithSshRetry(callable $callback, array $context = [], bool $throwError = true)`.
**Data Shape:** Config: `constants.ssh.max_retries`, `retry_base_delay`, `retry_max_delay`, `retry_multiplier`. ~26 lowercase-compared substring patterns.

### Decisive source
```php
$retryablePatterns = [
    'kex_exchange_identification', 'Connection reset by peer', 'Connection refused',
    'Connection timed out', 'Connection closed by remote host', ... 'Broken pipe',
    'No route to host', 'Network is unreachable', ..., 'Too many authentication failures',
    'SSH command failed with exit code: 255',
];
$lowerErrorOutput = strtolower($errorOutput);
foreach ($retryablePatterns as $pattern) {
    if (str_contains($lowerErrorOutput, strtolower($pattern))) return true;
}
return false;
...
$delay = min($baseDelay * pow($multiplier, $attempt), $maxDelay);
```

**Flow:** execute_remote_command wraps each command: catch RuntimeException|DeploymentException → if message matches a transport pattern AND attempts remain → log retry entry, re-check cancellation during the sleep, exponential backoff sleep → else rethrow. After exhaustion, status is conditionally updated to FAILED only where not already FINISHED (`where('status','!=',FINISHED)`), then last error throws. The generic `'SSH command failed with exit code: 255'` pattern exists because ssh(1) reports most connection failures as exit 255 with varying stderr. `executeWithSshRetry` is the reusable variant used by instant_remote_process helpers.
**Invariant:** Classification keys on ERROR MESSAGE SUBSTRINGS, not exit codes — remote command failures that print ordinary output never match, so only transport-layer breakage retries; backoff is capped; cancellation is honored between retries. Auth failures ("Permission denied, please try again", "Too many authentication failures") ARE retried — deliberate for flaky key distribution, surprising to porters.
**Probe:** `tests/Unit/SshRetryMechanismTest.php::test_retry_on_ssh_connection_errors / test_non_ssh_errors_are_not_retryable / test_exponential_backoff_calculation` pin membership and delay math per attempt.
**Retrieve:** search_graph project ext-coolify query "isRetryableSshError calculateRetryDelay" resolves trait methods in app/Traits/SshRetryable.php.

## Verdict
Adopt substring-based transport-error classification + capped exponential backoff + cancel-aware sleeps; tune the pattern list to your SSH client's messages; omit the Laravel config indirection.
