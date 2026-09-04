<!-- capsule-v2 -->
# SSH multiplexing lock — how is the per-server SSH master socket kept alive and lock-safe across workers?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** Many Horizon workers hit the same server — who owns establishing the ControlMaster connection, and how are stale sockets retired without killing the wrong process?

## SshMultiplexingHelper::ensureMultiplexedConnection / generateSshCommand
**Path/Symbol:** `app/Helpers/SshMultiplexingHelper.php:ensureMultiplexedConnection` (lines 26–65), `generateSshCommand` (211–250), `removeMuxFile` (93–109), `muxSocket` (347–350), retirement key helpers (285–310).
**Signature:** `public static function ensureMultiplexedConnection(Server $server): bool`, `public static function generateSshCommand(Server $server, string $command, bool $disableMultiplexing = false, ?int $commandTimeout = null): string`.
**Data Shape:** Socket path `/var/www/html/storage/app/ssh/mux/mux_<server.uuid>`; cache keys `ssh_mux_lock_<hostname>_<uuid>` (lock) and `ssh_mux_retiring_<sha256(hostname|pid|starttime|socket)>`; config knobs under `constants.ssh.*` (mux_enabled, mux_persist_time, mux_lock_ttl/timeout, mux_health_check_enabled).

### Decisive source
```php
return Cache::lock(self::connectionLockKey($server), config('constants.ssh.mux_lock_ttl'))
    ->block(config('constants.ssh.mux_lock_timeout'), function () use ($server) {
        if (self::connectionIsReusable($server)) return true;              // double-check INSIDE lock
        if (self::masterConnectionExists($server)) {
            return self::refreshMultiplexedConnection($server);            // ssh -O stop then re-establish
        }
        return self::establishNewMultiplexedConnection($server);
    });
} catch (LockTimeoutException) {
    Log::warning('SSH multiplexing lock timeout, falling back to non-multiplexed connection', ...);
    return false;                                                          // degrade, don't fail
}
```

**Flow:** generateSshCommand rejects disabled servers → validates/resyncs key file content vs DB + chmod 0600 → if mux enabled: ensureMultiplexedConnection (check reusable → acquire host-scoped lock → double-check → refresh or establish `ssh -fN -o ControlMaster=auto -o ControlPath=... -o ControlPersist=...` with optional cloudflared ProxyCommand) → append multiplexing options; any Throwable in the mux path logs and falls back to a plain connection. Command payload travels as `ssh ... 'bash -se' <<$DELIMITER` heredoc where DELIMITER = base64_encode(Hash::make($command)) with that delimiter stripped from the body.
**Invariant:** The establishment lock is per-hostname+server so parallel workers serialize socket creation but different servers never block each other; LockTimeout DEGRADES to non-multiplexed instead of failing. Retirement markers record pid+process-start-time (from /proc stat field 19) scoped by hostname+pid-namespace BEFORE `ssh -O stop`, and unmark on stop failure — this prevents PID-reuse from making one server's cleanup kill another's master. Health check (`isConnectionHealthy`) probes echo through the existing socket when enabled.
**Probe:** `tests/Feature/SshMultiplexingLockTest.php` (482 lines) exercises lock contention/fallback around ensureMultiplexedConnection; `tests/Unit/SshCommandInjectionTest.php` pins escapeshellarg wrapping of user@ip/port operands.
**Retrieve:** search_graph project ext-coolify query "ensureMultiplexedConnection generateSshCommand mux" → Method nodes at app/Helpers/SshMultiplexingHelper.php 26–65 / 211–250.

## Verdict
Adopt lock-guarded double-checked socket establishment + degrade-not-fail + start-time-scoped retirement markers as pure distributed-systems behavior; adapt Cache::lock to your lock provider; omit cloudflared tunnel flags unless you have the same topology.
