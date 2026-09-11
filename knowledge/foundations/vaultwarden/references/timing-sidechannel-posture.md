<!-- capsule-v2 -->
# Timing side-channel countermeasures — where does a Rust vault deliberately slow itself down, and why only on some paths?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Which response paths leak "does this user exist / is 2FA enrolled" through timing, and what's the mitigation pattern?

## Register-verification randomized sleep
**Path/Symbol:** `src/api/identity.rs:1057-1104` (`register_verification_email`), sleep block :1080-1090.
**Data Shape:** when `signups_verify` + mail enabled and the target email belongs to an EXISTING fully-registered user (private_key set), the handler sleeps a random 900–1100ms INSTEAD of sending mail; unregistered emails get the real send (variable time) — but the response shape (204 No Content) is identical.

### Decisive source
```rust
if user.as_ref().is_some_and(|u| u.private_key.is_some()) {
    // There is still a timing side channel here in that the code
    // paths that send mail take noticeably longer than ones that don't.
    // Add a randomized sleep to mitigate this somewhat.
    use rand::{RngExt, rngs::SmallRng};
    let mut rng: SmallRng = rand::make_rng();
    let sleep_ms: u64 = rng.random_range(900..=1100);
    tokio::time::sleep(tokio::time::Duration::from_millis(sleep_ms)).await;
} else {
    mail::send_register_verify_email(&data.email, &token).await?;
}
Ok(RegisterVerificationResponse::NoContent(()))
```

**Invariant:** the comment is honest — "mitigate this somewhat": mail latency variance still leaks more than the sleep hides; the defense narrows, not closes, the channel. Porters should note the asymmetry (registered→fake work, unregistered→real send) and consider sleeping BOTH arms for stronger parity.

## Login-path enumeration posture
**Path/Symbol:** `src/api/identity.rs:371-377, 409-415`: unknown user returns the same client message as wrong password ("Username or password is incorrect") but SKIPS PBKDF2 verification entirely — server-side timing still differs (no KDF work for unknown users); upstream accepts this at message level only. Disabled-user check runs BEFORE credential verification (identity.rs:381) — a disabled account rejects without KDF, another measurable difference.
**Invariant for porters:** decide explicitly which channels you close (messages), which you mask (randomized sleeps), which you accept (KDF-skip); document each — this codebase documents two of three in comments.

## Constant-time primitives elsewhere
**Path/Symbol:** `src/crypto.rs:112` (`ct_eq`) for API keys/recovery/remember tokens; ring pbkdf2::verify for password hashes; `hmac_sign` SHA-1 only for legacy Duo signatures.
**Probe:** `grep -c 'random_range(900..=1100)' src/api/identity.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "register_verification_email", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the honest-comment + targeted-mitigation pattern; adapt sleep ranges to your mail latency distribution; do NOT copy the one-arm-only sleep into a context with active enumeration tooling without measuring. Source pinned at `46d71107`; no test can pin timing behavior — recorded as inherent caveat.
