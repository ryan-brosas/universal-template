<!-- capsule-v2 -->
# Admin-panel session + web-vault gate — how does a separate admin surface authenticate, expire and self-diagnose?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How is the /admin surface isolated from user tokens and what keeps its sessions short?

## Dedicated issuer + config-driven lifetime
**Path/Symbol:** `src/auth.rs:56` (`JWT_ADMIN_ISSUER = {origin}|admin`), `:536-543` (`generate_admin_claims`, sub="admin_panel", exp = `CONFIG.admin_session_lifetime()` minutes), `decode_admin` :158; rate-limit lane `check_limit_admin` (ratelimit.rs:48); admin routes `src/api/admin.rs` (927 LOC incl. tests).
**Data Shape:** BasicJwtClaims only (nbf/exp/iss/sub) — no device, no sstamp; the admin cookie carries this token; every admin handler decodes with the admin ISSUER so a login JWT can never satisfy it (and vice versa).

### Decisive source
```rust
pub fn generate_admin_claims() -> BasicJwtClaims {
    let time_now = Utc::now();
    BasicJwtClaims {
        nbf: time_now.timestamp(),
        exp: (time_now + TimeDelta::try_minutes(CONFIG.admin_session_lifetime()).unwrap()).timestamp(),
        iss: JWT_ADMIN_ISSUER.to_string(),
        sub: "admin_panel".to_owned(),
    }
}
```

**Flow:** disabled admin token (`ADMIN_TOKEN` unset) ⇒ routes render "disabled" page; enabled ⇒ password form (constant-time token compare via ct_eq family) → set JWT cookie → panel issues diag diagnostics (the module's unit test `validate_web_vault_compare` pins version-comparison used for the "web vault is outdated" banner).
**Invariants:** (1) Session length is CONFIG-minutes with no refresh — re-auth forced; contrast 2h access tokens for users. (2) The admin lane has its OWN rate limiter so brute-forcing /admin cannot exhaust the shared budget. (3) Version compare treats `+build.N` suffixes with explicit ordering rules (10 assertions in test).
**Probe:** `grep -n 'fn validate_web_vault_compare' src/api/admin.rs | wc -l` → `1`.

## Web-vault static serving
**Path/Symbol:** `src/api/web.rs` (309 LOC): mounted vault at `web_vault_folder`, cache headers via util::Cached, 404 fallback to resources/404.
**Probe:** `grep -c 'web_vault' src/api/web.rs | head -1` → non-zero (serving plane).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "generate_admin_claims", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt purpose-isolated admin realm with short fixed TTL; adapt token transport to your framework's cookies; omit the diagnostics suite at your peril — it operationalizes the header/version contracts pinned in security-header-fairing.
