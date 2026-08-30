<!-- capsule-v2 -->
# Legacy hash migration on login — how do you upgrade password storage without a reset campaign?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How are legacy SHA-256 pepper-hashes verified and transparently upgraded to bcrypt?

## verify_password / hash_password / password_needs_rehash_check
**Path/Symbol:** `application/helpers/password_helper.php:28` (`hash_password`, 28–42), `:55` (`verify_password`, 55–75), `:84` (`password_needs_rehash_check`, 84–93).
**Signature:** `verify_password(string $salt, string $password, string $hash): bool`
**Data Shape:** New hashes: PHP `password_hash(PASSWORD_BCRYPT, cost 12)` — the `$salt` parameter is kept for signature compatibility but UNUSED by bcrypt. Legacy: `sha256(salt[0:len/2] . password . salt[len/2:])` iterated 100,000×.

### Decisive source
```php
// application/helpers/password_helper.php:61-75 — format-sniffed dual verification
if (preg_match('/^\$2[ayb]\$/', $hash)) {
    return password_verify($password, $hash);      // bcrypt path
}
$half = (int) (strlen($salt) / 2);
$legacy_hash = hash('sha256', substr($salt, 0, $half) . $password . substr($salt, $half));
for ($i = 0; $i < 100000; $i++) { $legacy_hash = hash('sha256', $legacy_hash); }
return hash_equals($legacy_hash, $hash);           // iterated legacy path
```

**Flow:** login → `verify_password` sniffs `$2a/$2y/$2b` prefix → mismatch-free legacy verification still returns true → caller (`Accounts::check_login` :71-78) runs `password_needs_rehash_check` and rewrites `user_settings.password` with a fresh bcrypt hash **in the same successful request**.
**Invariant:** migration is lazy (on successful login only — never on failure, so an attacker can't force rehashes), the salt stays in the row for rollback compatibility, and `MAX_PASSWORD_LENGTH=100` is enforced in BOTH hash and verify (bcrypt silently truncates at 72 bytes — the cap prevents silent-equivalent passwords). Comparison via `hash_equals`, not `===`. Porters who drop the iteration count change every legacy user's password validity.
**Probe:** `grep -c '100000' application/helpers/password_helper.php` (= 1: the legacy iteration bound at :70).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "verify_password", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt format-sniffed dual verify + lazy upgrade-on-success + length caps; adapt the legacy algorithm ONLY if migrating your own legacy scheme (the 100k iteration count is this repo's historical fact, not a recommendation); omit nothing else. Direct tests: none upstream.
