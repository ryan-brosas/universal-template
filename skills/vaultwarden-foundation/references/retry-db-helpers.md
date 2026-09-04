<!-- capsule-v2 -->
# Retry + DB-wait helpers — how do you wrap transient failures without retry storms?

**Source:** vaultwarden AGPL-3.0 `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory `ext-vaultwarden`. **Question:** What is the exact retry policy for generic fallible closures and for cold database pools?

## Two retry twins with different backoffs
**Path/Symbol:** `src/util.rs:731-750` (`retry`), `:752-776` (`retry_db`).
**Signature:** `pub fn retry<F: FnMut() -> Result<T,E>, T, E>(func: F, max_tries: u32) -> Result<T, E>` and async twin `retry_db<F, T, E: std::error::Error>`.

### Decisive source
```rust
// sync: 500ms fixed sleep between tries, block_on inside a Handle (safe under Rocket's runtime)
Handle::current().block_on(sleep(Duration::from_millis(500)));
...
// db: 1s sleep, warns each attempt, and NOTE the guard on zero:
if tries >= max_tries && max_tries > 0 { return Err(e); }
warn!("Can't connect to database, retrying: {e:?}");
sleep(Duration::from_secs(1)).await;
```

**Flow:** closure re-invoked until Ok or budget exhausted; `max_tries = 0` in retry_db means RETRY FOREVER (used at boot to wait for the DB to come up — main.rs startup); `tries >= max_tries` returns the LAST error unchanged.
**Invariants:** (1) No exponential backoff anywhere in these helpers — fixed cadence by design; heavier policies live in the callers if needed. (2) retry_db requires `E: std::error::Error` so it can warn-format generically. (3) The boot path deliberately uses infinite retry — porters must keep that out of request paths.
**Probe:** `grep -c 'max_tries > 0' src/util.rs` → `1`.

## UUID / date / misc glue
**Path/Symbol:** `util.rs:394` (`get_uuid` v4 simple), `:474-531` (`format_date` ISO with 'Z' suffix via naive+UTC, `parse_date` tolerant of missing fractional seconds), `:419` (`try_parse_string` NumberOrString coercion used for device_type where iOS sends "14" as STRING), `:668` (`deser_opt_nonempty_str` — null→None but empty-string→error? actually skips empty to None per FolderData bug workaround clients#8453), `:777` (`convert_json_key_lcase_first` recursive key renamer for org export "clients can't handle uppercase-first keys!!").
**Probe:** `grep -c 'pub fn try_parse_string' src/util.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vaultwarden", query: "retry_db", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-cadence split and the zero-means-infinite boot convention; adapt sleep constants; omit block_on usage under runtimes that forbid it.
