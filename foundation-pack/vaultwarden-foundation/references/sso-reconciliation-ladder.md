<!-- capsule-v2 -->
# SSO identity reconciliation ladder — when an OIDC login matches no account, an email-only account, or a conflicting SSO account, who wins?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How does a first SSO login attach to (or create) a local user without hijacking existing accounts?

## Four-way match ladder before any token is issued
**Path/Symbol:** `src/api/identity.rs:193-360` (`sso_login`), match block :208-252 (`SsoUser::find_by_identifier` → `find_by_mail` cascade).
**Data Shape:** `sso::exchange_code` returns `(SsoAuth row, user_infos{identifier, email, email_verified, user_name})`; `SsoUser { user_uuid, identifier }` is the binding table.

### Decisive source
```rust
let user_with_sso = match SsoUser::find_by_identifier(&user_infos.identifier, conn).await {
    None => match SsoUser::find_by_mail(&user_infos.email, conn).await {
        None => None,                                    // brand-new → provisioning path below
        Some((user, Some(_))) => {
            error!("Login failure (…), existing SSO user ({}) with same email ({})", …);
            err_silent!("Existing SSO user with same email", ErrorEvent { event: EventType::UserFailedLogIn })
        }
        Some((user, None)) if user.private_key.is_some() && !CONFIG.sso_signups_match_email() => {
            err_silent!("Existing non SSO user with same email", …)   // association disabled + real account
        }
        Some((user, None)) => match user_infos.email_verified {
            None if !CONFIG.sso_allow_unknown_email_verification() => err_silent!("Email verification status is unknown", …),
            Some(false) => err_silent!("Email is not verified by the SSO provider", …),
            _ => Some((user, None)),                     // ADOPT the passwordless/invited account
        },
    },
    Some((user, sso_user)) => Some((user, Some(sso_user))),  // normal returning SSO user
};
```

**Flow:** identifier hit → straight through 2FA (`twofactor_auth`) then `sso::redeem`. Email-only hit → three refusals (bound-elsewhere / real-account+match-disabled / unverified-email) else adoption. No hit → provision: `is_email_domain_allowed` gate → verified-status gates → `User::new(email)` with `verified_at=now` saved immediately; stub users (private_key none) get name/email refreshed from the IdP on each login and `mail::send_sso_change_email` fires when the IdP email changed.
**Invariants:** (1) An identifier may bind to exactly one user; email collisions NEVER re-bind silently — they err_silent with distinct messages per cause. (2) Adoption requires the target to be password-less-or-invited UNLESS `sso_signups_match_email` opts in. (3) Provisioning respects the domain whitelist even though the IdP authenticated the user.
**Probe:** `grep -c 'err_silent!' src/api/identity.rs` → `4`.

## Refresh-time revocation of SSO trust
**Path/Symbol:** `src/auth.rs:1301-1341` (`refresh_tokens` arms): SSO disabled ⇒ "SSO is now disabled, Login again using email and master password"; `sso_only` blocks password refreshes symmetrically.
**Probe:** `grep -c 'SSO is now' src/auth.rs` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "exchange_code", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identifier-first/email-second matching with explicit refusal taxonomy; adapt config toggles to your IdP posture; omit duo/iframe legacy paths. sso.rs/sso_client.rs internals (OIDC client plumbing, :473/:348 LOC) are pass-2 targets — this capsule pins the API-side decision ladder only.
