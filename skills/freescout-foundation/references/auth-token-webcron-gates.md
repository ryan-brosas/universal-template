<!-- capsule-v2 -->
# Auth-token & web-cron gates — how do stateless endpoints authenticate without a session?

**Source:** FreeScout AGPL-3.0 `master@ab2772536811d5de6e23121c5d086aeb50f3db2c`; Codebase Memory `ext-freescout`. **Question:** How does an in-app AJAX call survive an expired session, and how is the unauthenticated `schedule:run` HTTP trigger protected?

## TokenAuth middleware
**Path/Symbol:** `app/Http/Middleware/TokenAuth.php:18-49`.
**Signature:** `public function handle($request, Closure $next)`.
**Data Shape:** token = `urlencode(base64_encode("user_id:expiry:hash"))`; hash = `hash_hmac('sha256', "$user_id:$expiry", config('app.key') . $user->password)`.

### Decisive source
```php
// app/Http/Middleware/TokenAuth.php:21-46
if (!$request->user() && !empty($request->auth_token) && ... \Helper::isInApp($request)) {
    $parts = explode(':', urldecode(base64_decode($request->auth_token)));
    if (count($parts) !== 3) { return $next($request); }     // malformed → anonymous, NOT 401
    list($user_id, $expiry, $token_hash) = $parts;
    if (time() > (int)$expiry)            { return $next($request); }
    $user = User::find($user_id);
    if (!$user)                           { return $next($request); }
    $hash = hash_hmac('sha256', $user_id.':'.$expiry, config('app.key').$user->password);
    if (hash_equals($hash, $token_hash)) { \Auth::login($user); }
}
```
**Invariant:** the password hash is baked into the HMAC KEY — any password change invalidates every outstanding token for that user (free revocation). Failure mode is always "stay anonymous" (the normal auth stack then 401s), never a distinct error, so probing tokens reveals nothing. `isInApp()` restricts this restore path to requests from the bundled SPA/webview surface.

## Web-cron endpoint
**Path/Symbol:** `app/Http/Controllers/SystemController.php:388-404`.
```php
public function cron(Request $request) {
    if (empty($request->hash) || !\Helper::hashEquals($request->hash, \Helper::getWebCronHash())) {
        abort(404);   // constant-time compare; wrong hash looks like a missing route
    }
    $outputLog = new BufferedOutput();
    \Artisan::call('schedule:run', [], $outputLog);
    ...
}
```
The secret lives in the DB/options (generated per install) so rotating it doesn't need a deploy; a 404 (not 403) hides the endpoint's existence. Kernel-side twin guard: `schedule()` early-returns unless `\Helper::isRoute('system.cron')` or a real console `schedule:run` invocation (Kernel.php:33-38 + isScheduleRun :274-281) — web-triggered schedule ticks are first-class.
**Probe:** `grep -c "hash_hmac" app/Http/Middleware/TokenAuth.php` (= 1) and `grep -c "abort(404)" app/Http/Controllers/SystemController.php` (= 3 — cron arm at :396).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-freescout", query: "TokenAuth auth token", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt HMAC-over-secret-material token design with silent-failure semantics and 404-cloaked cron gate; adapt base64/urlencode envelope to JWT if desired but KEEP password-hash-in-key revocation; omit isInApp scoping only if your tokens travel over a narrower channel. Direct tests: none upstream for either gate.
