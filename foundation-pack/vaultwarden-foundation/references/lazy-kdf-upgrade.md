<!-- capsule-v2 -->
# Lazy KDF upgrade on login — how do stored iteration counts ratchet upward without a migration?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How does an instance raise its PBKDF2 work factor and migrate every user without an offline rehash job?

## Upgrade-on-successful-credential
**Path/Symbol:** `src/api/core/accounts.rs:1355-1367` (`kdf_upgrade`), call sites identity.rs:452 (password_login, only when `data.auth_request.is_none()`) and accounts.rs:1385 (`verify_password` endpoint).
**Signature:** `pub async fn kdf_upgrade(user: &mut User, pwd_hash: &str, conn: &DbConn) -> ApiResult<()>`.
**Data Shape:** compares STORED per-user `password_iterations` against current `CONFIG.password_iterations()`; only strictly-lower values upgrade — config decreases never downgrade users.

### Decisive source
```rust
pub async fn kdf_upgrade(user: &mut User, pwd_hash: &str, conn: &DbConn) -> ApiResult<()> {
    if user.password_iterations < CONFIG.password_iterations() {
        user.password_iterations = CONFIG.password_iterations();
        user.set_password(pwd_hash, None, false, None, conn).await?;
        if let Err(e) = user.save(conn).await { error!("Error updating user: {e:#?}"); }
    }
    Ok(())
}
```

**Flow:** client just proved the credential → server re-derives the hash under the NEW count from the SAME input (the client-side derived secret is deterministic) → saves; no security-stamp reset (`reset_security_stamp=false`), no key change (`new_key=None`), no logout fan-out — invisible to other sessions by design.
**Invariants:** (1) Upgrade runs ONLY after successful verification — never probe-and-upgrade. (2) It is skipped for auth-request (device-passkey) logins because those never present the master-password-derived secret. (3) The verify-password endpoint ALSO upgrades, catching API-only flows. (4) Save errors are logged but do NOT fail the login — the upgrade is best-effort.
**Probe:** `grep -c 'user.password_iterations < CONFIG.password_iterations()' src/api/core/accounts.rs` → `1`.

## Prelogin tells clients the parameters
**Path/Symbol:** `accounts.rs:1324-1344` (`prelogin`).
**Data Shape:** unknown email returns `CLIENT_KDF_TYPE_DEFAULT`/`CLIENT_KDF_ITER_DEFAULT` (600_000) with `"salt": null` — enumeration-safe constant response shape; known email returns the user's quartet so the client derives locally BEFORE calling /connect/token.
**Probe:** `grep -c 'CLIENT_KDF_ITER_DEFAULT' src/db/models/user.rs` → `2` (const + initializer).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "kdf_upgrade", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verify-then-ratchet as the zero-migration work-factor strategy; adapt the config source and default constants; omit the auth-request carve-out if you lack that flow. Deterministic probes executed at pin; no upstream test covers upgrade.
