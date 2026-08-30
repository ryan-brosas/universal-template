<!-- capsule-v2 -->
# PBKDF2 verification kernel — how does the server store and verify a master-password-derived secret without ever seeing the password?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Which KDF runs server-side, what exactly is hashed, and which comparison primitives must be constant-time?

## PBKDF2-HMAC-SHA256 over a client-side hash
**Path/Symbol:** `src/crypto.rs:12` (`hash_password`), `src/crypto.rs:21` (`verify_password_hash`), `src/db/models/user.rs:160` (`User::check_valid_password`), `src/db/models/user.rs:192` (`User::set_password`).
**Signature:** `hash_password(secret: &[u8], salt: &[u8], iterations: u32) -> Vec<u8>`; `verify_password_hash(secret, salt, previous, iterations) -> bool`.
**Data Shape:** `secret` is ALREADY the client-side derived hash (base64 string) — the server never receives the raw master password. Server salt = 64 random bytes generated once at `User::new` (`crypto::get_random_bytes::<64>`, user.rs:126). `password_iterations` is per-user i32 (default `CONFIG.password_iterations()`); output length fixed to SHA-256 (32 bytes). Zero iterations would panic (`NonZeroU32::expect("Iterations can't be zero")`).

### Decisive source
```rust
// src/crypto.rs
const DIGEST_ALG: pbkdf2::Algorithm = pbkdf2::PBKDF2_HMAC_SHA256;
pub fn verify_password_hash(secret: &[u8], salt: &[u8], previous: &[u8], iterations: u32) -> bool {
    let iterations = NonZeroU32::new(iterations).expect("Iterations can't be zero");
    pbkdf2::verify(DIGEST_ALG, iterations, salt, secret, previous).is_ok()
}
```
```rust
// src/db/models/user.rs — iteration count is cast unsigned from the stored i32
self.password_hash =
    crypto::hash_password(password.as_bytes(), &self.salt, self.password_iterations.cast_unsigned());
```

**Flow:** client derives local hash → sends as "password" → server PBKDF2s that value again with per-user salt+iterations → stores/compares the 32-byte result. Verification uses ring's `pbkdf2::verify`, which is constant-time in the digest comparison.
**Invariant:** changing `salt` invalidates every stored hash; `iterations` must be persisted alongside the hash because verification needs the exact count used at derivation (no versioned prefix — the count lives in its own column).
**Probe:** `grep -c 'PBKDF2_HMAC_SHA256' src/crypto.rs` → `1` (single const definition).

## Constant-time compare + HMAC-SHA1 legacy pair
**Path/Symbol:** `src/crypto.rs:112` (`ct_eq`), `src/crypto.rs:29` (`hmac_sign`).
**Data Shape:** `ct_eq<T: AsRef<[u8]>, U: AsRef<[u8]>>(a, b) -> bool` wraps `subtle::ConstantTimeEq`; used for API keys (`User::check_valid_api_key` user.rs:177), recovery codes (user.rs:169 lowercased first), Send remember-tokens, and the 2FA-remember token compare. `hmac_sign` is SHA-1 (`HMAC_SHA1_FOR_LEGACY_USE_ONLY`) hex — only for legacy Duo signature compatibility.
**Invariant:** any equality check on a bearer-capable secret MUST go through `ct_eq` (or ring verify) — never `==`. `check_valid_recovery_code` normalizes case by lowercasing the STORED value, not the input.
**Probe:** `grep -c 'subtle::ConstantTimeEq' src/crypto.rs` → `1`.

## Send password twin uses the same kernel with fixed 100k iterations
**Path/Symbol:** `src/db/models/send.rs:102` (`Send::set_password`), `send.rs:118` (`Send::check_password`).
**Data Shape:** `PASSWORD_ITER: i32 = 100_000` hard-coded; salt fresh 64 bytes per set; all three columns (`password_hash`,`password_salt`,`password_iter`) are Option and cleared together — `check_password` returns false unless ALL three are Some.
**Flow:** clearing a Send password sets all three to None; verification fails closed on partial state.
**Probe:** `grep -n 'PASSWORD_ITER: i32 = ' src/db/models/send.rs` → single hit `100_000`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "hash_password", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sided derivation (client hash → server PBKDF2) and per-user iteration column as the portable behavior; adapt the salt storage to your schema; omit the SHA-1 `hmac_sign` unless you must speak legacy Duo. Direct-test coverage caveat: upstream has no unit test for this kernel (tests exist only for web_vault_compare/obscure_email/is_global) — probes here are source pins.
