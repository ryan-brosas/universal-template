<!-- capsule-v2 -->
# Send access-token ladder — how do you gate one-time link access with a password and an atomic max-access counter?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How are Send (temporary encrypted share) tokens issued, what error taxonomy do clients see, and how is the access count race-free?

## Grant ladder with typed OAuth-ish errors
**Path/Symbol:** `src/auth/send.rs:68-116` (`SendTokens::generate_tokens`), error builders :48-66 (`expected_error`/`invalid_error`).
**Data Shape:** errors are JSON bodies `{kind:"expected_server", error:"invalid_request"|"invalid_grant", send_access_error_type: …}`; invalid_grant variants carry HTTP 404 + a `silent` flag controlling log noise. Access id is base64url-nopad UUID (`as_send_id` :31-38).

### Decisive source
```rust
let Some(mut send) = Send::find_by_uuid(&send_id, conn).await else { return Self::invalid_error(..., "send_id_invalid", false); };
if let Some(max_access_count) = send.max_access_count && send.access_count >= max_access_count {
    return Self::invalid_error(..., "send_id_invalid", true);   // silent: don't log maxed-out probes loudly
}
if !send.is_accessible() { return Self::invalid_error(..., "send_id_invalid", true); }
if send.password_hash.is_some() {
    match password {
        Some(ref p) if send.check_password(p) => { /* Nothing to do here */ }
        Some(_) => return Self::invalid_error(..., "password_hash_b64_invalid", false),
        None => return Self::expected_error("Password required", "password_hash_b64_required"),
    }
}
if !send.register_access(conn).await? { return Self::invalid_error(..., "send_id_invalid", true); }
Ok(Self { access_claims: generate_send_access_claims(&send_id) })  // 2-minute JWT, issuer …|send
```

**Flow:** `/connect/token` grant_type=`send_access` → unauthenticated rate-limit FIRST (identity.rs:110) → ladder above. Note the client sends the password ALREADY HASHED (pbkdf2 client-side, base64url) — server verifies against its own stored hash.
**Probe:** `grep -c 'send_id_invalid' src/auth/send.rs` → `5`.

## Atomic counter IS the race gate
**Path/Symbol:** `src/db/models/send.rs:237-262` (`register_access`), window check `is_accessible` :268-281.
**Signature:** `pub async fn register_access(&mut self, conn) -> Result<bool, Error>` — bool = admitted.
**Data Shape:** conditional UPDATE: `WHERE uuid = ? AND (max_access_count IS NULL OR access_count < max_access_count)` SET `access_count = access_count + 1, revision_date = now`; `updated == 0` ⇒ denied.

### Decisive source
```rust
diesel::update(sends::table)
    .filter(sends::uuid.eq(uuid))
    .filter(sends::max_access_count.is_null().or(sends::access_count.nullable().lt(sends::max_access_count)))
    .set((sends::access_count.eq(sends::access_count + 1), sends::revision_date.eq(revision_date)))
    .execute(conn)
```

**Invariants:** (1) The pre-check at grant time is advisory UX only; admission correctness lives in this single conditional UPDATE — N concurrent requests over a max=1 Send yield exactly one token. (2) In-memory `self.access_count` is bumped ONLY when updated>0, keeping the row cache honest. (3) `is_accessible` deliberately excludes max_access_count (doc comment: "consumed at token issuance") — disabled/expired/deletion-date checks only.
**Probe:** `grep -n 'sends::access_count.nullable().lt' src/db/models/send.rs | wc -l` → `1`.

## Downstream guard
**Path/Symbol:** `src/auth/send.rs:119-141` (`FromRequest for SendHeaders`) decodes the 2-minute send-issuer JWT for content fetches.
**Probe:** `grep -c 'decode_send' src/auth/send.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "register_access", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt conditional-UPDATE admission counters for any metered-link feature; adapt error taxonomy to your clients; omit the Bitwarden-specific error kinds. Probes executed from repo root at pin.
