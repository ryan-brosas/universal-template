<!-- capsule-v2 -->
# Emergency access + 2FA recovery code — how do you design a break-glass path that is itself rate-limited by time and policy?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How does the one-shot 2FA recovery code interact with org policy enforcement, and how does emergency access time-delay its own grants?

## Recovery code burns all second factors
**Path/Symbol:** `src/api/identity.rs:867-884` (`TwoFactorType::RecoveryCode` arm in twofactor_auth), `src/api/core/two_factor/mod.rs:116-127` (`generate_recover_code`), `src/db/models/user.rs:169-175` (`check_valid_recovery_code`).
**Data Shape:** single value `user.totp_recover` (base32 20 bytes, generated on first authenticator activation); comparison lowercases STORED value then `ct_eq`.

### Decisive source
```rust
Some(TwoFactorType::RecoveryCode) => {
    // Check if recovery code is correct
    if !user.check_valid_recovery_code(twofactor_code) { err!("Recovery code is incorrect. Try again.") }
    // Remove all twofactors from the user
    TwoFactor::delete_all_by_user(&user.uuid, conn).await?;
    enforce_2fa_policy(user, &user.uuid, device.atype, &ip.ip, conn).await?;
    log_user_event(EventType::UserRecovered2fa as i32, …).await;
    // Remove the recovery code, not needed without twofactors
    user.totp_recover = None; user.save(conn).await?;
}
```

**Flow:** valid code ⇒ ALL TwoFactor rows deleted (the code itself included — it exists only while factors exist), org 2FA policy re-evaluated immediately (can REVOKE membership if a policy requires 2FA and none remain), audit event, user saved.
**Invariants:** (1) Recovery code is consumed by USE even though it "just" removes factors — you can't reuse it next lockout; a NEW one is minted when 2FA is re-enabled. (2) Policy enforcement runs synchronously inside recovery so an org cannot be left holding a non-compliant member silently.
**Probe:** `grep -c 'UserRecovered2fa' src/api/identity.rs` → `1`.

## Emergency access wait-time model
**Path/Symbol:** `src/api/core/emergency_access.rs` (834 LOC whole-file plane), config jobs `emergency_notification_reminder_schedule` / `emergency_request_timeout_schedule` (config.rs:545-553), reminder+auto-confirm jobs in src/main.rs job scheduler.
**Data Shape:** grantor names grantee with `key_encrypted` escrow (same pattern as org reset); status machine invited→accepted→confirmed→recovered; `wait_time_days` gates recovery; two cron jobs: hourly reminders near expiry and timeout AUTO-CONFIRM of requests past their wait.
**Invariant:** the vault keys are escrowed at CONFIRMATION time (grantor re-encrypts to grantee pubkey) — the server can hand over ciphertext after the delay WITHOUT any grantor action at crisis time; auto-confirm makes silence consent.
**Probe:** `grep -cE 'emergency_(request_timeout|notification_reminder)_schedule:' src/config.rs` → `2` (table entries; validation sites use the non-colon names).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "EmergencyAccess", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt burn-on-use recovery with synchronous policy re-check; adapt emergency-access delays to your compliance needs; deep-dive emergency_access.rs internals (invite tokens, JWT claims `JWT_EMERGENCY_ACCESS_INVITE_ISSUER` already covered in jwt-issuer-realms) as pass-2 seam.
