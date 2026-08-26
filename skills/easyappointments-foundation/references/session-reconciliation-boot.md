<!-- capsule-v2 -->
# Session-existence guard + boot-time request gate — what must every controller constructor guarantee before app logic runs?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How does the base controller kill stale sessions and enforce the global rate limit on every request?

## EA_Controller boot sequence
**Path/Symbol:** `application/core/EA_Controller.php:66` (constructor, 66–92), `:94` (`ensure_user_exists`, 94–107).
**Signature:** `ensure_user_exists(): void` (private, runs inside constructor)
**Data Shape:** Session carries `user_id` (+ `role_slug`, `language`, `timezone` set at login). Storage dirs under `storage/` checked writable first.

### Decisive source
```php
// application/core/EA_Controller.php:69-92 — ordered boot ladder
parent::__construct();
$this->load->library('accounts');
$this->check_storage_writable();
$this->ensure_user_exists();      // ← session-vs-database reconciliation
$this->configure_timezone();
$this->configure_language();
$this->load_common_html_vars();
$this->load_common_script_vars();
rate_limit($this->input->ip_address());   // ← every request, defaults 100/120s
// :99-106 — the stale-session killer
if (!$user_id || !$this->db->table_exists('users')) { return; }
if (!$this->accounts->does_account_exist($user_id)) {
    session_destroy();
    abort(403, 'Forbidden');
}
```

**Flow:** storage writability → user-exists reconciliation → TZ/locale configuration → view vars → global rate limit. The reconciliation queries the DB for the session's user on EVERY authenticated request; a deleted/suspended account's very next request is destroyed+403, not just UI-hidden.
**Invariant:** authorization is re-anchored to live DB state each request — role changes or deletions take effect immediately without waiting for session TTL. `table_exists` guard keeps pre-install states from crashing. Rate limiting runs AFTER auth work here (contrast middleware-first frameworks): a flood still burns DB reads per request until the counter trips — porters wanting cheaper rejection must reorder deliberately.
**Probe:** `grep -n "session_destroy\|rate_limit(" application/core/EA_Controller.php | wc -l` (= 2 lines: :103 and :91).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "ensure_user_exists", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-request session-to-DB reconciliation + terminal rate-limit call; adapt abort/response helpers; omit CI3-specific loader plumbing. Direct tests: none upstream.
