<!-- capsule-v2 -->
# Argon2id cross-client parameter contract — which KDF constants are load-bearing across every platform?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** What must a new client replicate byte-for-byte so a vault encrypted on one platform unlocks on all others?

## Rust core defaults
**Path/Symbol:** `core/rust/src/argon2/mod.rs:31-51` (`argon2_hash_password`), doc comment :17-24.
**Signature:** `pub fn argon2_hash_password(password: &str, salt: &str) -> Result<String, Argon2Error>` → uppercase hex (64 chars = 32 bytes).
**Data Shape:** Params: m_cost 19456 KiB, t_cost 2, p_cost 1, output 32 bytes; Algorithm::Argon2id, Version::V0x13 (`0x13`). Salt is the raw UTF-8 bytes of the string; Argon2 rejects < 8-byte salts.

### Decisive source
```rust
// AliasVault default parameters
let params = Params::new(
    19456,    // m_cost (memory in KiB)
    2,        // t_cost (iterations)
    1,        // p_cost (parallelism)
    Some(32), // output length
)?;
let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
```

**Flow:** password+salt → Argon2id hash → hex → this digest becomes the `password_hash` input of `srp_derive_private_key` AND the base64 "passwordHashBase64" used for vault AES key derivation on clients.
**Invariants:** (1) The module doc states the contract outright: "Parameters must stay identical across all AliasVault clients." (2) Same constants appear in the TS layer's `DEFAULT_ENCRYPTION` JSON (`apps/browser-extension/src/utils/auth/SrpAuthService.ts:50-57`: `{"DegreeOfParallelism":1,"MemorySize":19456,"Iterations":2}`) and in `EncryptionUtility.deriveKeyFromPassword`'s default settings string + `type: 2` (Argon2id) selector (:20-49). (3) Server stores per-user `encryptionType`/`encryptionSettings` in the Vault row and returns them at login-initiate, so params can migrate per-user but MUST round-trip.
**Probe:** `grep -c '19456' core/rust/src/argon2/mod.rs` → `2`; `grep -c '19456' apps/browser-extension/src/utils/auth/SrpAuthService.ts` → `1`; `grep -c 'type: 2, // 0 = Argon2d, 1 = Argon2i, 2 = Argon2id' apps/browser-extension/src/utils/EncryptionUtility.ts` → `1`.

## Direct tests
**Path/Symbol:** `core/rust/src/argon2/mod.rs:53-82` (`test_hash_password_deterministic`, `test_hash_password_varies_with_inputs`, `test_short_salt_fails`).
**Invariant:** determinism per (password, salt); distinct outputs for changed password or salt; `"short"` (5 bytes) salt → `Argon2Error::InvalidParameter`.
**Probe:** `grep -c 'salt of at least 8 bytes' core/rust/src/argon2/mod.rs` → `1`; `grep -c 'Algorithm::Argon2id' core/rust/src/argon2/mod.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "argon2_hash_password", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the {19456, 2, 1, 32} Argon2id parameter tuple and the hash-feeds-SRP-private-key flow as an immutable contract; adapt the argon2 library per platform; omit the WASM/uniffi plumbing. Caveat: no cargo runner in inspo clone; deterministic probes substitute for the in-file test suite.
