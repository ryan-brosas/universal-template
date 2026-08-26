<!-- capsule-v2 -->
# Login anti-enumeration + session rotation — what must the credential-validation path do beyond checking the password?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How does Login::validate defeat username enumeration, injection-shaped usernames, and session fixation?

## Login::validate ladder
**Path/Symbol:** `application/controllers/Login.php:66` (`validate`, 66–169), rate-limit gate at :72.
**Signature:** `validate(): void` (POST only, `method('post')` guard).
**Data Shape:** Inputs: `username` (string), `password`, optional `captcha`/`altcha_payload`; output JSON `{success: bool, message?}`.

### Decisive source
```php
// application/controllers/Login.php:118-157 — format gate → dual backend → constant-ish failure → rotation
if (!preg_match('/^[a-zA-Z0-9_@.\-]+$/', $username) || strlen($username) > 255) {
    throw new InvalidArgumentException(lang('invalid_credentials_provided'));
}
// ...
$user_data = $this->accounts->check_login($username, $password);
if (empty($user_data)) { $user_data = $this->ldap_client->check_login($username, $password); }
if (empty($user_data)) {
    log_message('info', 'Failed login attempt for username: ' . $username . ' from IP: ' . $this->input->ip_address());
    usleep(random_int(100000, 300000)); // 100-300ms randomized delay
    json_response(['success' => false, 'message' => lang('invalid_credentials_provided')]);
    return;
}
$this->session->sess_regenerate(true); // delete old session id
session($user_data);
```

**Flow:** strict rate limit (5/5min) → captcha/ALTCHA when enabled (ALTCHA verified server-side via `altcha_client->verify`) → username charset allowlist (`[a-zA-Z0-9_@.\-]`, ≤255) → password length cap (`MAX_PASSWORD_LENGTH=100`) → local DB then LDAP fallback → identical shaped failure for both "no such user" and "wrong password" → success rotates session id deleting the old one before storing identity.
**Invariant:** the SAME generic message covers unknown-user and bad-password (no oracle), padded by a RANDOMIZED 100–300 ms sleep so timing can't separate them either; bcrypt cost 12 with transparent legacy rehash on successful login (`Accounts::check_login` :70-78 calls `password_needs_rehash_check` → rewrites hash). Session regeneration uses `sess_regenerate(true)` — destroy-old-session semantics, killing fixation via stolen pre-auth ids.
**Probe:** `grep -c "usleep(random_int" application/controllers/Login.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "apply_login_rate_limit check_login", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt allowlist+cap, DB→LDAP fallback, uniform randomized-delay failures, and delete-on-regenerate; adapt usleep to your framework's sleep; omit captcha specifics if you use a different challenge. Direct tests: none upstream.
