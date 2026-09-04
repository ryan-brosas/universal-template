<!-- capsule-v2 -->
# Error taxonomy macros — how do 25 error kinds become one HTTP responder without leaking internals?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How does a single Error type carry user message, log detail, HTTP code, audit event and silence flag — and what do the err! macro family expand to?

## make_error! declarative kind table
**Path/Symbol:** `src/error.rs:14-77` (`make_error!` macro + invocation), `Error { message, kind, code, event, silent }`.
**Data Shape:** each variant declares source-printing (`has_source`/`no_source`) and client-render fn; default code 400; `From<(name, err)>` auto-impls mean `?` on diesel/reqwest/openssl/… errors just works.

### Decisive source
```rust
make_error! {
    Empty(Empty):     no_source, serialize,
    Simple(String):   no_source,  api_error,
    Compact(Compact): no_source,  compact_api_error,
    CustomHttpClient(CustomHttpClientError): has_source, api_error,
    Json(Value):      no_source,  serialize,   // special returns like the 2FA challenge body
    Db(DieselErr):    has_source, api_error,
    ...
}
```

**Flow:** `err!("msg")` logs AND returns `Error::new_msg`; `err!("usr", log_value)` splits user-visible from internal detail (log shows both, client sees only usr_msg); `err_silent!` skips the error! log line entirely (used for expected failures like SSO email collisions); `err_code!(msg, 429)` sets status; `err_json!(body, msg)` wraps a Value for the Json variant (2FA challenges); `err_handler!` is the GUARD-side twin returning `Outcome::Error((Unauthorized, …))`; `err_discard!` drains the request BODY before responding so clients don't see connection resets on early rejection.
**Invariants:** (1) User/log message separation is the leak boundary — `Display` renders only the user message; `{:#?}` Debug adds `[CAUSE]` for logs. (2) `silent` travels with the error and is checked in the Responder, not at construction sites. (3) The Responder maps unknown codes back to 400 and ALWAYS answers JSON.
**Probe:** `grep -c 'macro_rules!' src/error.rs` → `7` (err, err_silent, err_code, err_discard, err_json, err_handler + make_error).

## Client-shaped envelopes
**Path/Symbol:** `src/error.rs:223-306` (`ApiErrorResponse` / `CompactApiErrorResponse` manual Serialize).
**Data Shape:** Bitwarden clients demand redundant shape: top-level `message`, `validationErrors{"":[msg]}`, `errorModel{message,object:"error"}` plus empty OAuth-ish fields; compact variant drops three empties. Hand-written serialize "more efficient than having a larger struct" (comment) and avoids json!() per error.
**Invariant:** changing envelope keys breaks official clients — this duplication IS the wire contract.
**Probe:** `grep -c 'exceptionStackTrace' src/error.rs` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "ErrorKind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-Error-with-policy-fields and the user/log split; adapt macro names to your idiom; omit Bitwarden envelope fields only when your clients allow. Whole-file read at pin; no upstream tests (error paths exercised indirectly by the two unit-tested modules).
