<!-- capsule-v2 -->
# Password-login ladder — in what order do scope, rate-limit, user lookup, auth-request bypass, KDF upgrade and email-verification interlock?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** What is the exact gate order of a master-password login, and where does the device-passkey (auth request) path diverge?

## Ordered gates
**Path/Symbol:** `src/api/identity.rs:362-482` (`password_login`), `:60` (`login` grant router), `:775-908` (`twofactor_auth`).
**Signature:** `async fn password_login(data, user_id: &mut Option<UserId>, conn, ip, client_version) -> JsonResult`.
**Data Shape:** failure carries `ErrorEvent { event: EventType::UserFailedLogIn }` so the login attempt lands in the event log even when rejected; `user_id` is an out-param set as soon as the user row exists so successes AND failures log the actor.

### Decisive source (gate sequence, condensed)
```rust
AuthMethod::Password.check_scope(data.scope.as_ref())?;          // 1. exact scope match "api offline_access"
crate::ratelimit::check_limit_login(&ip.ip)?;                     // 2. per-IP throttle
let Some(mut user) = User::find_by_mail(username.trim(), ...)     // 3. identical error for unknown user
if !user.enabled { err!("This user has been disabled", ...) }      // 4. disabled check BEFORE credential work
// 5. EITHER auth-request access-code path OR password verify:
//    auth_request checks: ownership + approved + not-expired(5min) + request_ip == ip + check_access_code(password)
} else if !user.check_valid_password(password) { err!("Username or password is incorrect. Try again", ...) }
if data.auth_request.is_none() { kdf_upgrade(&mut user, password, conn).await?; }   // 6. lazy KDF bump
// 7. signups_verify ladder: resend verification email throttled by last_verifying_at + login_verify_count,
//    then ALWAYS err!("Please verify your email before trying again.")
let twofactor_token = twofactor_auth(...).await?;                 // 8. 2FA challenge / remember token
let auth_tokens = auth::AuthTokens::new(&device, &user, AuthMethod::Password, data.client_id);
authenticated_response(&user, &mut device, auth_tokens, twofactor_token, conn, ip).await
```

**Invariants:** (1) Unknown-user and wrong-password produce the SAME message ("Username or password is incorrect") but different log payloads — enumeration resistance is at message level only. (2) The auth-request branch substitutes the AUTH REQUEST's access code for the master password and pins `request_ip == ip` — a handshake approved on another network cannot be redeemed here; expiry is creation_date+5 minutes. (3) Email-verification enforcement happens AFTER credential success — unverified users burn full PBKDF2 work. (4) `kdf_upgrade` runs ONLY on real-password logins, never auth-request logins.
**Probe:** `grep -c 'Username or password is incorrect' src/api/identity.rs` → `2`.

## Authenticated response contract
**Path/Symbol:** `src/api/identity.rs:484-581` (`authenticated_response`).
**Data Shape:** emits access/refresh tokens plus vault-bootstrap keys: `Key` (akey), `PrivateKey`, Kdf quartet, `MasterPasswordPolicy`, `AccountKeys.publicKeyEncryptionKeyPair`, `UserDecryptionOptions{HasMasterPassword, MasterPasswordUnlock}`; new-device email fires when `device.is_new()` and mail enabled (hard-fails only if `require_device_email`); push registration for existing devices.
**Probe:** `grep -c 'MasterKeyEncryptedUserKey' src/api/identity.rs` → `2` (password + api-key responses).

## API-key login twin deliberately bypasses 2FA
**Path/Symbol:** `identity.rs:584-773` (`api_key_login` → `user_api_key_login` / `organization_api_key_login`), comment "Note that API key logins bypass 2FA."; no refresh_token returned — CLI repeats client_credentials on expiry.
**Probe:** `grep -n 'bypass 2FA' src/api/identity.rs | wc -l` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "password_login", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering (scope→throttle→lookup→enabled→verify→upgrade→verify-email→2FA) as portable behavior; adapt the auth-request substitution to your own device-handshake scheme; omit Bitwarden response fields you don't need but keep their SHAPE if Bitwarden clients must talk to you.
