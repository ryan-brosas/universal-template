<!-- capsule-v2 -->
# Master-password policy merge — how do per-org policies combine into one effective constraint without ordering surprises?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** When a user belongs to several orgs each with a MasterPassword policy, what single policy does the client enforce?

## Reduce with max/OR semantics
**Path/Symbol:** `src/api/mod.rs:78-126` (`MasterPasswordPolicy` struct + `master_password_policy()`), consumed at identity.rs:509 (`authenticated_response`) and accounts.rs:1393 (`verify_password`).
**Signature:** `async fn master_password_policy(user: &User, conn: &DbConn) -> Value` — private helper; exposed inside login response and verify-password response.
**Data Shape:** fields `min_complexity: Option<u8>, min_length: Option<u32>, require_lower/upper/numbers/special: bool, enforce_on_login: bool`; source rows are JSON blobs in org_policy.data filtered by `OrgPolicyType::MasterPassword` over accepted-and-confirmed memberships.

### Decisive source
```rust
json!(master_password_policies.into_iter().reduce(|acc, policy| {
    MasterPasswordPolicy {
        min_complexity: acc.min_complexity.max(policy.min_complexity),
        min_length: acc.min_length.max(policy.min_length),
        require_lower: acc.require_lower || policy.require_lower,
        require_upper: acc.require_upper || policy.require_upper,
        ...,
        enforce_on_login: acc.enforce_on_login || policy.enforce_on_login,
    }
}))
```

**Flow:** collect active policies → parse (unparseable rows silently DROPPED via filter_map) → reduce (empty ⇒ SSO config fallback `sso_master_password_policy_value`, else `{}`) → force `"Object": "masterPasswordPolicy"` key with PascalCase note ("Upstream still uses PascalCase here").
**Invariants:** (1) Reduction is order-independent because max and OR are commutative/associative — no "strictest wins by list position" bugs. (2) None-handling: `Option::max` picks the larger present value; if either side is None the result may be None — a policy that only sets flags doesn't invent complexity minimums. (3) The server does NOT validate passwords against this policy — it only REPORTS it; enforcement is client-side at creation/change time.
**Probe:** `grep -c 'enforce_on_login: acc.enforce_on_login || policy.enforce_on_login' src/api/mod.rs` → `1`.

## Protected-action re-auth primitive
**Path/Symbol:** `src/api/mod.rs:51-72` (`PasswordOrOtpData::validate`), backed by `protected_actions::validate_protected_action_otp` (delete-if-valid flag per caller).
**Data Shape:** exactly ONE of master_password_hash | otp must be present ("No validation provided" otherwise); the SAME proof can be reused across a multi-step flow or consumed on first use — `delete_if_valid` is caller's choice ("This is different per caller", doc comment).
**Invariant:** sensitive endpoints (api-key rotate, sstamp reset, 2FA enrollment) share one validation struct so adding a new protected action = reuse, not a new scheme.
**Probe:** `grep -c 'No validation provided' src/api/mod.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "master_password_policy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt commutative policy reduction; adapt field set; keep the report-only posture unless you also port client-side checks server-side deliberately.
