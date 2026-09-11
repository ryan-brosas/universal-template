<!-- capsule-v2 -->
# Two-factor challenge protocol — how do you demand 2FA over an OAuth token endpoint without breaking clients that have not enrolled anything?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** What exact JSON tells a Bitwarden client "provide a second factor", and how are provider usability, remember-tokens and incomplete-login tracking wired?

## Provider usability gate
**Path/Symbol:** `src/api/core/two_factor/mod.rs:39-68` (`is_twofactor_provider_usable`), `:174-207` (`enforce_2fa_policy`), `:243+` (`send_incomplete_2fa_notifications`).
**Data Shape:** usability is per-provider AND config-dependent: Authenticator/RecoveryCode always; Email only if `_enable_email_2fa`; Duo (user or org) needs non-empty host/ik/sk in provider data OR global duo creds; YubiKey needs global client id+secret; Webauthn needs platform support; Remember only if not disabled; all U2F/challenge sub-types hard false.

### Decisive source
```rust
TwoFactorType::Duo | TwoFactorType::OrganizationDuo => {
    provider_data.and_then(|raw| serde_json::from_str::<DuoProviderData>(raw).ok())
        .is_some_and(|duo| !duo.host.is_empty() && !duo.ik.is_empty() && !duo.sk.is_empty())
        || has_global_duo_credentials()
}
```

**Flow inside twofactor_auth (`src/api/identity.rs:775`):** no factors at all → `enforce_2fa_policy` (org TwoFactorAuthentication policy auto-REVOKES non-admin members without 2FA, mailing them) and return None → else `TwoFactorIncomplete::mark_incomplete` records the attempt BEFORE validation → filter to enabled+usable ids → empty → "No enabled and usable two factor providers…" → selected = requested provider or FIRST usable → provider-specific validate → `mark_complete`.
**Invariants:** (1) An enabled-but-unusable provider (e.g. Duo creds deleted) is invisible to the challenge, not an error. (2) Remember/RecoveryCode are excluded from the "usable list" membership check but handled as special selected types. (3) Incomplete tracking writes BEFORE validation so abandoned logins are observable; the cron job emails them after `incomplete_2fa_time_limit` minutes.
**Probe:** `grep -c 'mark_incomplete\|mark_complete' src/api/identity.rs` → `2`.

## Challenge envelope
**Path/Symbol:** `identity.rs:913-1005` (`json_err_twofactor`).
**Data Shape:** HTTP error whose JSON body is `{error:"invalid_grant", error_description:"Two factor required.", TwoFactorProviders:[ids], TwoFactorProviders2:{"<id>": metadata|null}, MasterPasswordPolicy:{...}}`. Metadata per provider: Webauthn→assertion request options; Duo iframe→{Host,Signature} or OIDC {AuthUrl}; YubiKey→{Nfc}; Email→obscured address, with auto-send ONLY when email is the sole provider AND client <2025.5.0 (newer clients poll `/two-factor/send-email-login` — semver gate on the `Bitwarden-Client-Version` header).
**Probe:** `grep -c 'TwoFactorProviders2' src/api/identity.rs` → `7`.

## Remember-token validation
**Path/Symbol:** `identity.rs:851-866` (`TwoFactorType::Remember` arm), `auth.rs:456-475` (`generate_2fa_remember_claims`, 30-day device-scoped JWT).
**Data Shape:** stored on the Device row (`twofactor_remember`); validity requires `crypto::ct_eq(token, code)` AND `decode_2fa_remember(code)` OK AND claims.sub==device.uuid AND claims.user_uuid==user.uuid AND config allows remember.
**Invariant:** any failure DELETES the stored remember token immediately (saved right away because err_json aborts the request) — a bad remember attempt burns the device's remembered state.
**Probe:** `grep -n 'delete_twofactor_remember' src/api/identity.rs | wc -l` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "is_twofactor_provider_usable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-map challenge envelope and config-sensitive provider usability; adapt provider set to your stack; omit legacy U2f variants. All cited ranges verified at pin; probes executed from repo root.
