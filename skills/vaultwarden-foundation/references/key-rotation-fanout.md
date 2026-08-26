<!-- capsule-v2 -->
# Key-rotation fan-out — what must be re-encrypted when a user changes their master password, and why is there no transaction?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Which encrypted-at-rest artifacts depend on the master key, and in what order does the server rewrite them?

## RotateAccount payload
**Path/Symbol:** `src/api/core/accounts.rs:884-1004` (`post_rotatekey`), request structs :776-830 (`KeyData` → `RotateAccountUnlockData`/`RotateAccountKeys`/`RotateAccountData` + `old_master_key_authentication_hash`).
**Data Shape:** one request carries EVERYTHING: re-encrypted folders, ciphers (personal only — org ciphers skipped), sends, emergency-access grantee keys, org reset-password keys, plus the new wrapped account key and new auth hash.

### Decisive source (order of operations)
```rust
// TODO: See if we can wrap everything within a SQL Transaction. If something fails it should revert everything.
if !headers.user.check_valid_password(&data.old_master_key_authentication_hash) { err!("Invalid password") }
Cipher::validate_cipher_data(&data.account_data.ciphers)?;   // pre-validate import BEFORE mutating anything
let (existing_ciphers, existing_folders, existing_emergency_access, existing_memberships, existing_sends) = ...;
existing_memberships.retain(|m| m.reset_password_key.is_some());  // rotate reset keys ONLY where enrolled
validate_keydata(&data, &existing_*, &headers.user)?;             // full referential check, still no writes
for folder_data ... { saved_folder.name = ...; save }             // 1. folders
for emergency_access_data ... { key_encrypted update; save }      // 2. emergency access
for reset_password_data ... { membership.reset_password_key; save}// 3. org recovery keys
for send_data ... { update_send_from_data(..., UpdateType::None)} // 4. sends
for cipher_data if organization_id.is_none() {                    // 5. personal ciphers only
    // Prevent triggering cipher updates via WebSockets by settings UpdateType::None
    update_cipher_from_data(..., UpdateType::None).await?; }
user.private_key = Some(...); user.set_password(new_auth_hash, Some(new_wrapped_key), true, None, &conn); // 6. account
let save_result = user.save(&conn).await;
nt.send_logout(&user, Some(&headers.device), &conn).await;        // everyone except acting device logs out
```

**Invariants:** (1) Validate-everything-then-write ordering minimizes partial rotation, but the code is honest: NO SQL transaction wraps it (two TODO comments) — a mid-way failure leaves mixed encryption that the client must retry. (2) Org ciphers are excluded because their key comes from the ORG key, not the user's. (3) `UpdateType::None` suppresses WebSocket notifications for every rotated object — clients are force-logged-out instead; notifying would push stale-key state to live sessions. (4) Membership retain filters to enrolled members so unenrolled orgs are silently skipped rather than erroring.
**Probe:** `grep -c 'TODO' src/api/core/accounts.rs | head -1` and `grep -n 'Ideally we.d do everything after this point in a single transaction' src/api/core/accounts.rs` → exactly 1 hit (:903 region).

## Password-change sibling does NOT touch objects
**Path/Symbol:** `accounts.rs:604-639` (`post_password`): verifies OLD hash, sets NEW hash+key, stamp-reset with route exception, logout-except-device — but rotates nothing else; used when the client knows old+new and objects keep the same symmetric key (password change ≠ key change in Bitwarden's model unless the client chooses rotation).
**Probe:** `grep -c 'get_api_webauthn' src/api/core/accounts.rs` → `1` (single allow_next_route list entry; the route registration + handler use different identifiers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "post_rotatekey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-first fan-out with notification suppression; adapt the artifact list to your schema; DO port the honesty marker — document non-atomicity at the seam instead of pretending a transaction exists.
