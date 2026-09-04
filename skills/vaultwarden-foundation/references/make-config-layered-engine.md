<!-- capsule-v2 -->
# make_config! layered config engine — how do env vars, a JSON file and admin-panel edits merge with declared precedence and privacy masking?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** How does one declarative table generate accessors, env parsing, file persistence, form rendering and support dumps — and who wins when layers conflict?

## Declarative table + four none-actions
**Path/Symbol:** `src/config.rs:58-500` (`make_config!` macro), table body :502+ (~200 items), `Config { inner: RwLock<Inner> }` with `_env: ConfigBuilder`, `_usr: ConfigBuilder`, `_overrides: Vec<&'static str>`.
**Signature (DSL):** `name: Type, editable, action, <default>;` where action ∈ `def` (unwrap_or default) | `auto` (compute fn over partially built ConfigItems, e.g. database_url from data_folder) | `option` | `generated` (always computed, input ignored — e.g. `_ip_header_enabled = ip_header != "none"` :673).
**Data Shape:** doc comments double as UI labels (`Friendly Name |> Description`, split on `|>`); type token `Pass` renders as password field and serializes as `"***"`.

### Decisive source (merge precedence)
```rust
fn merge(&self, other: &Self, show_overrides: bool, overrides: &mut Vec<&str>) -> Self {
    let mut builder = self.clone();
    if let v @Some(_) = &other.$name {
        builder.$name = v.clone();
        if self.$name.is_some() { overrides.push(stringify!([<$name:upper>])); }  // BOTH set → record
    }
    ...
}
// update_config:  env.merge(&user_builder).build()  → validate → write inner → persist builder JSON to config.json
```

**Flow:** boot reads ENV_FILE (.env) then env vars into `_env`; `config.json` (saved admin edits) deserialized leniently (missing/duplicate keys tolerated) into `_usr`; effective config = env merged with usr (usr WINS per-field; conflicts recorded in `_overrides` and warned at boot). `clear_non_editable` wipes non-editable fields from incoming panel payloads. Persistence stores the USER builder only — env re-applies on every boot.
**Invariants:** (1) Precedence is FILE-over-ENV by explicit design ("environment variables are being overridden by the config.json file") — inverted from most stacks; porters must not "fix" this silently. (2) `build()` normalizes: domain trailing slash stripped, whitelists lowercased, deprecated `icon_blacklist_regex` copied to `http_request_block_regex`. (3) Every accessor clones out of an RwLock read guard — no long-held locks across await points (comments enforce short lock scopes).
**Probe:** `grep -c 'fn clear_non_editable' src/config.rs` → `1`.

## Support dump privacy mask
**Path/Symbol:** `config.rs:410-460` (`get_support_json`, `privacy_mask`), PRIVACY_CONFIG const list.
**Data Shape:** Pass types auto-mask to "***"; listed String keys (database_url, smtp_host, sso_authority…) get char-level masking that preserves scheme shape: first ≤11 chars keep ':' (and '/' up to 13 after a colon), commas survive, everything else → '*'. Comment: faster than regex by orders of magnitude.
**Invariant:** support diagnostics can be pasted publicly WITHOUT leaking secrets, but URLs stay structurally readable for debugging.
**Probe:** `grep -c 'fn privacy_mask' src/config.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "make_config", limit: 10, fields: ["signature", "name", "file"] });
```
(BM25 resolves the macro-generated fns; cite `src/config.rs:58` directly.)

## Verdict
Adopt single-table generation with recorded-conflict merging; adapt layer names/persistence to your runtime; omit the Rocket-specific RwLock pattern only for your framework's equivalent. Signup gating (`is_signup_allowed` :1538: whitelist OVERRIDES signups_allowed flag entirely) lives in the same impl block — read together.
