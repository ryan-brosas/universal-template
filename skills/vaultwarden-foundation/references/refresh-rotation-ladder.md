<!-- capsule-v2 -->
# Refresh-token rotation ladder — how does a 30-day refresh token survive device diversity, SSO revocation and security-stamp rotation?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** When a client presents a refresh token, which checks run, in what order, and what invalidates the whole chain?

## AuthTokens pair + mobile-aware validity
**Path/Symbol:** `src/auth.rs:1251` (`AuthTokens`), `src/auth.rs:44-46` (`DEFAULT_REFRESH_VALIDITY` 30d / `MOBILE_REFRESH_VALIDITY` 90d / `DEFAULT_ACCESS_VALIDITY` 2h), `src/auth.rs:1301` (`refresh_tokens`).
**Signature:** `pub async fn refresh_tokens(ip: &ClientIp, refresh_token: &str, client_id: Option<String>, conn: &DbConn) -> ApiResult<(Device, AuthTokens)>`.
**Data Shape:** `RefreshJwtClaims { sub: AuthMethod (OrgApiKey|Password|Sso|UserApiKey), device_token: String, token: Option<TokenWrapper> }`; access claims embed `sstamp`, `device`, `devicetype`, `client_id`. Refresh validity chosen by `device.is_mobile()`. Access-token lifetime shorter than BW's 5-minute floor logs a warning (`LoginJwtClaims::new`, auth.rs:243).

### Decisive source
```rust
let auth_tokens = match refresh_claims.sub {
    AuthMethod::Sso if CONFIG.sso_enabled() && CONFIG.sso_auth_only_not_session() => {
        AuthTokens::new(&device, &user, refresh_claims.sub, client_id)
    }
    AuthMethod::Sso if CONFIG.sso_enabled() => {
        sso::exchange_refresh_token(&device, &user, client_id, refresh_claims).await?
    }
    AuthMethod::Sso => err!("SSO is now disabled, Login again using email and master password"),
    AuthMethod::Password if CONFIG.sso_enabled() && CONFIG.sso_only() => err!("SSO is now required, Login again"),
    AuthMethod::Password => AuthTokens::new(&device, &user, refresh_claims.sub, client_id),
    _ => err!("Invalid auth method, cannot refresh token"),
};
```

**Flow:** decode refresh JWT (login issuer) → look up Device by `refresh_claims.device_token` → save device (touches `updated_at`) → load user → method-and-config dispatch above → return new pair. Decode failure logs the IP and returns silent "Invalid refresh token".
**Invariants:** (1) The device lookup is keyed on the refresh token stored in the DB row — a token whose device row vanished is dead even if the JWT still validates. (2) `reset_security_stamp` calls `Device::rotate_refresh_tokens_by_user` (user.rs:217) — every stamp rotation kills ALL refresh tokens for that user; this is the enforcement backstop for password changes. (3) SSO disablement mid-session is detected at REFRESH time, not access time — clients get an explicit "Login again" error.
**Probe:** `grep -n 'rotate_refresh_tokens_by_user' src/db/models/user.rs src/db/models/device.rs | wc -l` → `2`.

## Identity-side wrapper enforces the OAuth error envelope
**Path/Symbol:** `src/api/identity.rs:139-190` (`refresh_login`), identity.rs:60-131 (`login` grant_type router).
**Data Shape:** missing/invalid refresh must return JSON `{"error": "invalid_grant"}` with HTTP 400 — Bitwarden clients key on this exact shape (comment cites bitwarden/clients api.service.ts).
**Flow:** `/connect/token` routes by `grant_type`: `refresh_token` | `password` | `client_credentials` | `authorization_code` (SSO) | `send_access`, each with its own required-field ladder before dispatch.
**Probe:** `grep -c 'invalid_grant' src/api/identity.rs` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "refresh_tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer chain (JWT validity → DB device-token existence → auth-method/config gate) as portable behavior; adapt validity constants to your product; omit the SSO-specific arms if you have no IdP. Runner caveat stands: no upstream test exercises this path; probes are source pins at pin `46d71107`.
