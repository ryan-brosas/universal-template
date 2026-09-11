<!-- capsule-v2 -->
# Two-tier rate limiting — when do you use the global per-IP limiter and when a stricter endpoint-local counter?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How are request floods throttled globally vs login attempts locally, and what are the failure postures?

## rate_limit helper + Login::apply_login_rate_limit
**Path/Symbol:** `application/helpers/rate_limit_helper.php:28` (`rate_limit`, 28–78), `application/core/EA_Controller.php:91` (global call), `application/controllers/Login.php:176` (`apply_login_rate_limit`, 176–208).
**Signature:** `rate_limit(string $ip, int $max_requests = 100, int $duration = 120): void`
**Data Shape:** File-cache driver keys: global `rate_limit_key_<ip>` + window-expiry twin `rate_limit_tmp_<ip>` (colons stripped); login `login_attempts_<ip>` with colons/dots → underscores, 300s TTL.

### Decisive source
```php
// application/helpers/rate_limit_helper.php:33-37,73-76 — config-gated, CLI-exempt, hard exit
$rate_limiting = $CI->config->item('rate_limiting');
if (!$rate_limiting || is_cli()) { return; }
// ...
if ($requests > $max_requests) {
    header('HTTP/1.0 429 Too Many Requests');
    exit();
}
```
vs the login twin (`Login.php:196-207`): fixed 5 attempts / 300 s, throws RuntimeException (caught by validate() → JSON error), and cache-driver failures only log — "Log cache errors but don't block login".

**Flow:** EVERY EA_Controller request runs `rate_limit($this->input->ip_address())` with defaults (:91) → sensitive endpoints layer a stricter private method on top (`Booking_cancellation.php:72`, `Privacy.php:43`, `Login.php:72`). Window reset = expiry-twin timestamp comparison; first request seeds count=1 with TTL=duration and the twin at duration.
**Invariant:** two deliberate failure postures: global limiter is fail-CLOSED on config but silently skips when disabled/CLI; login limiter is fail-OPEN on cache errors (availability over strictness for auth UX). The global limiter kills the request with a raw 429+exit (no JSON envelope); the login one throws so the standard JSON error path renders. Porters who unify them lose one property or the other.
**Probe:** `bash -c 'grep -rc "apply_login_rate_limit" application/controllers/Login.php'` (= 2: call :72 + def :176; the global limiter rides every request via EA_Controller :91).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "rate_limit", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-tier split with its distinct failure postures; adapt file-cache to Redis keeping the colon-stripped key hygiene; omit nothing else. Direct tests: none upstream.
