<!-- capsule-v2 -->
# Security-stamp exception grace window — how does a password change avoid logging out the very device that performed it?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** After the security stamp rotates (invalidating all tokens), how do multi-step client flows complete their follow-up requests without re-authenticating?

## Stamp check inside the request guard
**Path/Symbol:** `src/auth.rs:627-752` (`FromRequest for Headers`, stamp block :707-744), `src/db/models/user.rs:192-244` (`set_password` / `set_stamp_exception` / `reset_stamp_exception`).
**Data Shape:** `UserStampException { routes: Vec<String>, security_stamp: String, expire: i64 }` serialized as JSON into `users.stamp_exception`. The JWT carries the stamp at issue time (`sstamp` claim). Guard fires whenever `user.security_stamp != claims.sstamp`.

### Decisive source
```rust
if Utc::now().timestamp() > stamp_exception.expire {
    // expired → remove from DB so later requests skip this branch entirely, then reject
    let mut user = user; user.reset_stamp_exception();
    if let Err(e) = user.save(&conn).await { error!("Error updating user: {e:#?}"); }
    err_handler!("Stamp exception is expired")
} else if !stamp_exception.routes.contains(&current_route.to_owned()) {
    err_handler!("Invalid security stamp: Current route and exception route do not match")
} else if stamp_exception.security_stamp != claims.sstamp {
    err_handler!("Invalid security stamp for matched stamp exception")
}
```

**Flow:** password change calls `set_password(..., reset_security_stamp=true, allow_next_route=Some(vec!["post_rotatekey","get_contacts","get_public_keys","get_api_webauthn"]))` (accounts.rs:617-626) → stamp rotated + refresh tokens wiped + exception JSON written with 2-minute expiry → the requesting device's NEXT requests still carry the OLD stamp in their JWT; the guard matches route name against the allow-list and old-stamp against the recorded one → after expiry the exception self-destructs on first touch.
**Invariants:** (1) Route match is by Rocket route NAME (`request.route().name`), e.g. `"revision_date"` used by set-password flow (accounts.rs:447 comment "allow revision-date to use the old security_timestamp"). (2) The exception authorizes ONLY routes in its list — any other endpoint rejects. (3) Expiry is checked FIRST and lazily cleans up — no background sweeper needed.
**Probe:** `grep -n 'Stamp exception is expired' src/auth.rs | wc -l` → `1`.

## Logout exclusion of the acting device
**Path/Symbol:** `src/api/core/accounts.rs:631-633` (`post_password` send_logout), accounts.rs:1006-1028 (`post_sstamp` deletes ALL devices instead).
**Data Shape:** `nt.send_logout(&user, Some(&headers.device), &conn)` passes the acting device so the logout fan-out skips it; manual stamp reset (`post_sstamp`) passes None AND `Device::delete_all_by_user`.
**Invariant:** password/KDF/rotate-key flows preserve the initiating session via BOTH mechanisms (stamp exception + device-scoped logout); explicit sstamp reset is the nuclear option that spares nothing.
**Probe:** `grep -c 'send_logout(&user, Some(&headers.device)' src/api/core/accounts.rs` → `3` (password, kdf, rotatekey).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "stamp_exception", limit: 10, fields: ["signature", "name", "file"] });
```
(BM25 resolves the migration nodes; cite `src/auth.rs:707-744` directly for the guard.)

## Verdict
Adopt route-scoped, time-boxed stamp exceptions as the pattern for destructive credential flows; adapt the route-name matching to your router's identifiers; omit the Bitwarden-specific route list. Source wins over graph: the guard logic lives only in `Headers::from_request`, confirmed at pin `46d71107`; no upstream test covers it.
