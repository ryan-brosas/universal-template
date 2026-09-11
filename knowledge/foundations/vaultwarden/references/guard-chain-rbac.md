<!-- capsule-v2 -->
# Rocket guard chain — how does a type-driven auth ladder express member/admin/manager/owner without a single if-else at the route?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How is per-endpoint authorization composed so the compiler, not call-site discipline, enforces that every handler checked identity?

## Guard composition stack
**Path/Symbol:** `src/auth.rs:627` (`Headers`), `:766` (`OrgHeaders`), `:826` (`AdminHeaders`), `:877` (`ManagerHeaders` + `ManagerHeadersLoose` :930), `:993` (`OwnerHeaders`), `:1020` (`OrgMemberHeaders`), `:754` (`OrgIdGuard`).
**Signature:** each implements `FromRequest` returning `Outcome<Self, &'static str>`; higher guards `try_outcome!(LowerGuard::from_request(request).await)` — delegation not duplication.
**Data Shape:** `Headers { host, device, user, ip }`; `OrgHeaders` adds `membership_type/status/membership`. Role predicates live on OrgHeaders: `is_member()` (status != Revoked && type >= User), `is_confirmed_and_admin()`, `is_confirmed_and_manager()`, `is_confirmed_and_owner()` (Owner equality, not >=).

### Decisive source
```rust
fn is_member(&self) -> bool {
    // Only allow not revoked members, we can not use the Confirmed status here
    // as some endpoints can be triggered by invited users during joining
    self.membership_status != MembershipStatus::Revoked && self.membership_type >= MembershipType::User
}
fn is_confirmed_and_owner(&self) -> bool {
    self.membership_status == MembershipStatus::Confirmed && self.membership_type == MembershipType::Owner
}
```

**Flow:** `Headers` (JWT→device→user→stamp) → `OrgHeaders` (org_id from path param 1 or `organizationId` query via `get_org_id` :748; membership row load; unknown atype/status = "corrupted DB"/"revoked or invalid" 401s) → role guards. `AdminHeaders` requires confirmed+admin; `OwnerHeaders` confirmed+EXACT owner; `ManagerHeaders` additionally resolves `<col_id>` (path param 3 or query) and checks `Collection::is_coll_manageable_by_user`, while `ManagerHeadersLoose` skips collection check for endpoints without one and offers `from_loose(h, collections, conn)` to re-check a submitted LIST.
**Invariants:** (1) Revoked status fails ALL org guards even though `is_member` deliberately allows Invited (comment: joining endpoints) — only `!= Revoked` endpoints pass. (2) Downcast pattern: every role guard implements `From<T> for Headers` so handlers can widen. (3) Org id extraction order is path-first-query-second with UUID validation on both. (4) Missing org id in a dual-personal/org endpoint → `OrgIdGuard` FORWARDS (404) instead of erroring, enabling route fallback to the personal variant.
**Probe:** `grep -c "impl<'r> FromRequest<'r> for" src/auth.rs` → `14`.

## Why this matters for porters
A porter adding an endpoint picks the guard type and the compiler forces the auth check — there is no way to read `headers.user` without having passed `Headers`. The ladder encodes the whole RBAC matrix: personal (Headers), any-active-member (OrgMemberHeaders), manager±collection (Manager/Loose), admin, owner.
**Probe:** `grep -n 'is_coll_manageable_by_user' src/auth.rs | wc -l` → `2` (guard + from_loose).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "OrgHeaders", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt guard-type-as-authorizations; adapt `get_org_id`/`get_col_id` extraction to your framework's path/query API; omit the Rocket Forward semantics only if you lack route-fallback. Coverage clean on all cited ranges; behavior pinned by source reading at pin `46d71107` (no upstream integration tests).
