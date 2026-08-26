<!-- capsule-v2 -->
# Device handshake (auth request) — how does a passwordless device get approved by an already-unlocked client?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** What is the request/approve/redeem lifecycle of an AuthRequest, and how does the server verify the approving user without their master password?

## AuthRequest row + access-code derivation
**Path/Symbol:** `src/db/models/auth_request.rs` (`AuthRequest`, 207 LOC), `check_access_code`; API surface accounts.rs routes :70-77 (`post_auth_request`, `get_auth_request`, `put_auth_request`, `get_auth_request_response`, `get_auth_requests[_pending]`); redemption ladder in `password_login` (identity.rs:385-407).
**Data Shape:** row carries `user_uuid, request_ip, creation_date, approved: Option<bool>, key/keys, master_password_hash: Option<String>, access_code fields` — the new device posts a public key + optional master-password hash; the approving client encrypts the vault keys to that public key.

### Decisive source (redemption gates inside password_login)
```rust
if let Some(ref auth_request_id) = data.auth_request {
    let Some(auth_request) = AuthRequest::find_by_uuid_and_user(auth_request_id, &user.uuid, conn).await else { err!("Auth request not found. Try again.") };
    let expiration_time = auth_request.creation_date + chrono::Duration::minutes(5);
    let request_expired = Utc::now().naive_utc() >= expiration_time;
    if auth_request.user_uuid != user.uuid
        || !auth_request.approved.unwrap_or(false)
        || request_expired
        || ip.ip.to_string() != auth_request.request_ip      // same-IP redemption pin
        || !auth_request.check_access_code(password)          // access code REPLACES the master password
    { err!("Username or access code is incorrect. Try again", … UserFailedLogIn) }
} else if !user.check_valid_password(password) { … }
// kdf_upgrade deliberately skipped when data.auth_request.is_none() == false
```

**Flow:** new device POSTs auth-request (gets id + fingerprint phrase for the user to compare) → user approves from an unlocked device (PUT sets approved + returns keys encrypted to requester pubkey; may also store master_password_hash re-encryption) → new device calls /connect/token grant=password with auth_request id and ACCESS CODE as the password field → five-gate check above → normal token issuance.
**Invariants:** (1) Redemption is pinned to the REQUESTING IP — approval cannot be laundered through a different network. (2) Five-minute TTL bounds the approval window. (3) The access code is checked via its own verifier (not the user's PBKDF2 hash), so the master password never transits the passwordless path. (4) KDF upgrade is skipped on this branch because no real master-password secret was presented.
**Probe:** `grep -c 'request_ip' src/api/identity.rs` → `1`.

## Known-device probe endpoint
**Path/Symbol:** `accounts.rs:1408-1430` (`get_known_device` + `KnownDevice` guard).
**Data Shape:** unauthenticated; answers bool "is this (email, device uuid) pair known" so clients can label new-device prompts; email must resolve AND device belong to that user.
**Probe:** `grep -n 'find_by_uuid_and_user(&device.uuid' src/api/core/accounts.rs | wc -l` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "AuthRequest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt approve-then-redeem with IP pinning + short TTL; adapt key transport to your crypto envelope; omit the known-device hint at your UX's peril (new-device phishing resistance depends on it).
