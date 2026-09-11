<!-- capsule-v2 -->
# TOTP anti-replay time-step ledger — how does a 30-second code become single-use across a ±1 step drift window?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** Where is "this TOTP was already used" stored, and what makes replay impossible without a dedicated table?

## Last-used step on the TwoFactor row
**Path/Symbol:** `src/api/core/two_factor/authenticator.rs:117-175` (`validate_totp_code`), `:101-115` (`validate_totp_code_str` numeric gate), `src/db/models/two_factor.rs` (`TwoFactor.last_used` column).
**Signature:** `pub async fn validate_totp_code(user_id, totp_code: &str, secret: &str, ip, conn) -> EmptyResult`.
**Data Shape:** secret is base32 (20 bytes enforced at enrollment); code 6 digits; window `steps = i64::from(!CONFIG.authenticator_disable_time_drift())` → ±1 unless drift disabled (then 0); `time_step = now/30 + step`.

### Decisive source
```rust
if generated == totp_code && time_step > twofactor.last_used {
    if step != 0 { warn!("TOTP Time drift detected. The step offset is {step}"); }
    // Save the last used time step so only totp time steps higher then this one are allowed.
    twofactor.last_used = time_step;
    twofactor.save(conn).await?;
    return Ok(());
} else if generated == totp_code && time_step <= twofactor.last_used {
    warn!("This TOTP or a TOTP code within {steps} steps back or forward has already been used!");
    err!(... UserFailedLogIn2fa);
}
```

**Flow:** strict `>` comparison against the persisted monotone high-water mark means each 30-second slot validates at most once; the match-and-save is sequential in the async context (single row update) — no compare-and-set needed because two concurrent same-code requests both compute the same time_step and only one can satisfy `>` before save; the loser re-reads? No — both may pass in a race, but the window is ±1 slot and the practical replay surface is one reuse within ~30s, accepted upstream.
**Invariants:** (1) Replay rejection is an EXPLICIT branch with its own warning and event type (`UserFailedLogIn2fa`) — not a generic failure. (2) Disabling time-drift tolerance sets steps=0 so ONLY the current slot computes. (3) Enrollment path (`activate_authenticator` :52-95) validates a token with the NEW key BEFORE saving, requires exactly 20 decoded bytes, and generates the recovery code in the same transaction path.
**Probe:** `grep -n 'time_step > twofactor.last_used' src/api/core/two_factor/authenticator.rs | wc -l` → `1`.

## str-vs-code split
**Path/Symbol:** authenticator.rs:101-115.
**Data Shape:** `validate_totp_code_str` first rejects non-numeric strings ("TOTP code is not a number") then delegates — the inner function trusts shape.
**Probe:** `grep -c 'char::is_numeric' src/api/core/two_factor/authenticator.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "validate_totp_code", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt last-used-step persistence as the minimal anti-replay ledger; adapt storage to your two-factor table; omit the config toggle only with care — removing drift tolerance strands drifted clients. No upstream unit test covers validation; probes are source pins at `46d71107`.
