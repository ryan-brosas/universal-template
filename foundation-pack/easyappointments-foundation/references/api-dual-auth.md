<!-- capsule-v2 -->
# Dual-mode API authentication — how do you accept both a static bearer token and Basic credentials on one endpoint family?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** What is the auth ladder for API v1 and what happens to non-admin Basic users?

## Api::auth
**Path/Symbol:** `application/libraries/Api.php:65` (`auth`, lines 65–94), `:101` (`get_bearer_token`, 101–114), `:121` (`get_authorization_header`, 121–148), `:154` (`request_authentication`, 154–159).
**Signature:** `auth(): void`
**Data Shape:** Bearer: global `setting('api_token')` vs `Authorization: Bearer <token>`. Basic: `$_SERVER['PHP_AUTH_USER'/'PHP_AUTH_PW']`. Failure: `WWW-Authenticate: Basic realm="Easy!Appointments"` + `HTTP/1.0 401` + exit.

### Decisive source
```php
// application/libraries/Api.php:69-90 — token first, then Basic-with-role-gate
$api_token = setting('api_token');
$provided_token = $this->get_bearer_token();
if (!empty($api_token) && !empty($provided_token) && hash_equals($api_token, $provided_token)) {
    return; // timing-safe static-token path
}
$username = $_SERVER['PHP_AUTH_USER'] ?? null;
$password = $_SERVER['PHP_AUTH_PW'] ?? null;
if (empty($username) || empty($password)) { throw new RuntimeException('Missing required credentials', 401); }
$user_data = $this->CI->accounts->check_login($username, $password);
if (empty($user_data['role_slug']) || $user_data['role_slug'] !== DB_SLUG_ADMIN) {
    throw new RuntimeException('The provided credentials do not match any admin user', 401);
}
```

**Flow:** every v1 controller constructor runs `$this->api->auth()` before any action (e.g. `Appointments_api_v1.php:39`). Any Throwable inside the try falls through to `$this->request_authentication()` which emits the 401 challenge and exits.
**Invariant:** three-tier contract — (1) bearer token must match a single global setting via `hash_equals` (timing-safe, but the token is shared/static, no per-key revocation); (2) Basic creds must resolve to role `admin` exactly (`DB_SLUG_ADMIN`) — providers/secretaries with valid creds are REJECTED; (3) everything else gets a Basic challenge. The header reader walks `$_SERVER['Authorization']` → `HTTP_AUTHORIZATION` → `apache_request_headers()` with ucwords-normalized keys because nginx/fastcgi and old Android clients surface it differently.
**Probe:** `grep -c "hash_equals\|DB_SLUG_ADMIN" application/libraries/Api.php` (= 2).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "hash_equals api auth", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ladder order (token → Basic → admin-gate → 401 challenge) and the multi-source header reader; adapt the static token to your secret store (per-key hashing is strictly better); omit nothing else. Direct tests: none upstream.
