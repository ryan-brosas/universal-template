<!-- capsule-v2 -->
# Org recovery reset — how does an admin replace a member's master password without ever learning it, and what stops abuse?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** What is the enrollment → escrow → reset chain for organization password recovery?

## Enrollment stores the ESCROWED key, never the password
**Path/Symbol:** `src/api/core/organizations.rs:3129-3196` (`put_reset_password_enrollment`), `src/db/models/org_policy.rs:320` (`org_is_reset_password_auto_enroll`).
**Data Shape:** `Membership.reset_password_key: Option<String>` — the member's account key encrypted with the ORG public key. Empty string normalizes to None; withdraw requires no OTP but auto-enroll policy BLOCKS withdrawal ("Reset password can't be withdrawn due to an enterprise policy"); enrollment WITH a key demands `PasswordOrOtpData` proof.

### Decisive source
```rust
let reset_password_key = match reset_request.reset_password_key {
    None => None,
    Some(ref key) if key.is_empty() => None,
    Some(key) => Some(key),
};
if reset_password_key.is_none() && OrgPolicy::org_is_reset_password_auto_enroll(&org_id, &conn).await {
    err!("Reset password can't be withdrawn due to an enterprise policy");
}
if reset_password_key.is_some() {
    PasswordOrOtpData { master_password_hash: ..., otp: ... }.validate(&headers.user, true, &conn).await?;
}
membership.reset_password_key = reset_password_key;
```
```rust
// org_policy.rs — auto-enroll reads the policy's JSON data payload
Ok(opts) => { return policy.enabled && opts.auto_enroll_enabled; }
```

**Flow:** enroll (member, authenticated, proves password/OTP) → admin fetches `/reset-password-details` (kdf params + `resetPasswordKey` + org `encryptedPrivateKey`) → admin wraps new key and calls `/recover-account`.
**Probe:** `grep -n 'enterprise policy' src/api/core/organizations.rs | wc -l` → `1`.

## Reset execution ladder
**Path/Symbol:** `organizations.rs:2988-3054` (`put_recover_account` gate + `recover_account` body), permission pair :3092-3127.
**Signature:** `async fn recover_account(org_id, member_id, headers: AdminHeaders, reset_request, conn, nt)`.
**Data Shape:** only `reset_master_password && !reset_two_factor` supported; everything else "Unsupported operation".

### Decisive source
```rust
check_reset_password_applicable_and_permissions(&org_id, &member_id, &headers, &conn).await?; // mail on + policy enabled + rank check
if member.reset_password_key.is_none() { err!("Password reset not or not correctly enrolled") }
if member.status != (MembershipStatus::Confirmed as i32) { err!("Organization user must be confirmed for password reset functionality") }
// Sending email before resetting password to ensure working email configuration and the resulting
// user notification. Also this might add some protection against security flaws and misuse
if let Err(e) = mail::send_admin_reset_password(...) { err!(...) }
user.set_password(reset_request.new_master_password_hash.as_str(), Some(reset_request.key), true, None, &conn).await?;
user.save(&conn).await?;
nt.send_logout(&user, None, &conn).await;
log_event(EventType::OrganizationUserAdminResetPassword, ...)
```

**Invariants:** (1) Permission matrix: Owner resets anyone; Admin resets members at or below Admin (`target_user.atype <= MembershipType::Admin`) — an admin cannot reset another admin? No: `<= Admin` INCLUDES admins; only Owner targets are out of an Admin's reach. (2) Notification mail is sent BEFORE mutation and its failure ABORTS the reset — a broken SMTP can't silently strip someone's vault access. (3) Reset rotates stamp with NO route exception and logs out ALL devices (None passed), plus audit event. (4) Applicability requires mail ENABLED + ResetPassword policy row enabled — email-disabled instances refuse org recovery outright (check_reset_password_applicable :3112-3125).
**Probe:** `grep -c 'Sending email before resetting password' src/api/core/organizations.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "recover_account", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt public-key escrow + pre-mutation notification + ranked permission ladder; adapt policy storage shape; omit the deprecated `/reset-password` route alias. All ranges read whole-file at pin `46d71107`.
