<!-- capsule-v2 -->
# Registration invitation-take ladder — how do stub accounts, admin invitations and open signup compose without a TOCTOU on "does this user exist"?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** When an invited-but-unregistered email finally registers, which checks decide admission and in what order?

## Dual-shape register payload
**Path/Symbol:** `src/api/core/accounts.rs:107-247` (`RegisterData` + `RegisterDataCompat` untagged enum + `fold()`), `:140-160` (Old shape with serde aliases `userSymmetricKey`/`masterPasswordHash`), `:163+` (Cur shape `master_password_authentication`/`master_password_unlock`).
**Data Shape:** untagged serde tries Cur FIRST? — no: variant order in the enum is `RegisterDataOld` then `RegisterDataCur`, but Old has `#[serde(flatten)] kdf` so deserialization succeeds per-field presence; `unprocessable()` cross-checks that authentication.kdf == unlock.kdf AND both salts equal the lowercased trimmed email, returning 422 on mismatch.
**Invariant for porters:** one endpoint serves two client generations via a compat fold — never fork the route; fold accessors (`hash()`, `kdf()`, `key()`) hide which wire shape arrived.

### Decisive source
```rust
let mut user = match User::find_by_mail(&email, &conn).await {
    Some(user) => {
        if !user.password_hash.is_empty() { err!("Registration not allowed or user already exists") }
        if let Some(token) = data.org_invite_token.as_ref() {
            let claims = decode_invite(token)?;
            if claims.email == email { email_verified = true; user } else { err!("Registration email does not match invite email") }
        } else if Invitation::take(&email, &conn).await {
            Membership::accept_user_invitations(&user.uuid, &conn).await?;
            user
        } else if CONFIG.is_signup_allowed(&email)
            || (CONFIG.emergency_access_allowed() && EmergencyAccess::find_invited_by_grantee_email(&email, &conn).await.is_some()) {
            user
        } else { err!("Registration not allowed or user already exists") }
    }
    None => {
        // Order is important here; the invitation check must come first
        // because the vaultwarden admin can invite anyone, regardless of other signup restrictions.
        if Invitation::take(&email, &conn).await || CONFIG.is_signup_allowed(&email) || pending_emergency_access.is_some() {
            User::new(&email, None)
        } else { err!("Registration not allowed or user already exists") }
    }
};
// Make sure we don't leave a lingering invitation.
Invitation::take(&email, &conn).await;
```

**Flow:** token validation first when `email_verification` (register/finish): exactly ONE of {email-verification token | emergency-access pair | org-invite pair} may be present — any other combination errors ("Registration is missing required parameters"). Name length capped at 50 chars to keep JWTs small (#2419). Password-hint policy checked BEFORE invitation consumption so a policy failure doesn't burn the invite. Then the ladder above → `set_kdf_data` → `set_password(..., reset_security_stamp=true)` → keys/hint/name → verified_at → welcome mail (+auto-activate email 2FA if org-required).
**Invariants:** (1) `Invitation::take` is consume-on-read — double registration races resolve because the second take returns false. (2) Existing-user-with-empty-password_hash = invited STUB account; it can complete registration but ONLY through the same admission ladder. (3) The trailing unconditional `Invitation::take` guarantees no orphan invite survives ANY successful path.
**Probe:** `grep -c 'Invitation::take' src/api/core/accounts.rs` → `3`.

## KDF floor validation is separate from storage
**Path/Symbol:** `accounts.rs:642-676` (`set_kdf_data`).
**Data Shape:** PBKDF2 iterations ≥ 100_000 hard error; Argon2id needs iterations ≥1 AND memory 15..=1024 MB AND parallelism 1..=16, both REQUIRED; non-Argon2 types get memory/parallelism nulled out.
**Probe:** `grep -n 'must be at least 100000' src/api/core/accounts.rs | wc -l` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "RegisterData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stub-completion + consume-on-read invitations; adapt the token zoo (org/emergency/email-verify) to your flows; omit the legacy wire shape only after your clients migrate. Source verified whole-range :258-443 at pin.
