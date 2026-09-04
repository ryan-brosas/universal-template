<!-- capsule-v2 -->
# Governor three-lane rate limiting — why does the unauthenticated bucket exist separately from login, and what does check_key actually cost?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How is per-IP throttling wired so anonymous endpoints get their own budget and login failures cannot starve other lanes?

## Three static limiters
**Path/Symbol:** `src/ratelimit.rs:12-27` (LIMITER_LOGIN / LIMITER_ADMIN / LIMITER_UNAUTHENTICATED LazyLocks), checks at :30 (`check_limit_unauthenticated`), :39 (`check_limit_login`), :48 (`check_limit_admin`).
**Signature:** each `check_limit_*(ip: &IpAddr) -> Result<(), Error>`; on exhaustion `err_code!("…", 429)` — a raw HTTP 429 with JSON error body.
**Data Shape:** governor `RateLimiter<IpAddr, DashMapStateStore<IpAddr>, DefaultClock>` keyed per IP; quota = one cell per `CONFIG.*_ratelimit_seconds` with burst `*_max_burst`. All three constructed via `LazyLock` so config is read once at first use.

### Decisive source
```rust
pub fn check_limit_unauthenticated(ip: &IpAddr) -> Result<(), Error> {
    match LIMITER_UNAUTHENTICATED.check_key(ip) {
        Ok(()) => Ok(()),
        Err(_e) => { err_code!("Too many requests", 429); }
    }
}
```

**Flow / placement:** `send_access` grant and `register/send-verification-email` call `check_limit_unauthenticated` BEFORE any DB work (identity.rs:110, identity.rs:1063); password/SSO/API-key logins call `check_limit_login` after scope validation (identity.rs:197, :368, :587); admin endpoints use the third lane. The ClientIp feeding these keys already went through trusted-proxy resolution.
**Invariants:** (1) Lane separation means hammering an anonymous endpoint never locks a legitimate user out of logging in. (2) `check_key` is the non-consuming variant of governor's API in effect here only because every caller checks then acts — a rejected request still consumed a cell; do not "retry on 429" clientside without backoff. (3) Zero-valued config would panic at construction ("Non-zero … seconds/burst") — misconfiguration fails at startup, not under load.
**Probe:** `grep -c 'check_limit_unauthenticated' src/api/identity.rs` → `2`.

## Contrast posture with the easyappointments twin
**Path/Symbol:** same file, whole module 55 LOC.
**Data Shape:** vaultwarden's limiter is in-memory DashMap — resets on restart, per-process; no distributed coordination. Fail-CLOSED for over-limit (429) and there is no bypass for CLI/config-disabled peers (unlike some stacks).
**Probe:** `wc -l < src/ratelimit.rs` → `55`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "check_limit_login", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt static three-lane keyed limiters with startup-fail config validation; adapt limits to your traffic; omit the specific lane split only if your endpoint taxonomy differs materially. Source pin verified; upstream ships no test for this module.
