<!-- capsule-v2 -->
# DB secrets store — how do you store tenant/agent/version-scoped API keys Fernet-encrypted in the shared relational store with a working sync bridge and wildcard fallback?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where do UI-entered API keys actually live, how are they encrypted/scoped, and why does `get_secret_sync` spawn a thread instead of just running the coroutine?

## Encrypted, scoped, agent-wildcarded rows
**Path/Symbol:** `src/cuga/backend/storage/secrets_store.py` (`_fernet` :41-52; `ensure_schema` :73-95; `get_secret` :98-142; `get_secret_sync` :145-180; `set_secret` :183-232; `delete_secret` :277-299).
**Signature:** `get_secret(secret_id, *, tenant_id=None, instance_id=None, agent_id=None, version="*") -> str | None`; `set_secret(secret_id, value, ...)` raises RuntimeError without a key; `delete_secret(...) -> bool`.
**Data Shape:** PK `(tenant_id, instance_id, agent_id, version, id)`; `agent_id='*'` rows are shared fallbacks; `encrypted_value BYTEA/BLOB`; `tags JSONB/TEXT`. Dialect differences handled by `_is_prod(store)` (class-name check) + placeholder rewrites (`?` → `$N`) — SQL is written ONCE in sqlite style.

### Decisive source
```python
# :41-52 — encryption is OPTIONAL and read-side degrades to None (never plaintext)
def _fernet():
    key_env = getattr(sec, "db_encryption_key_env", "CUGA_SECRET_KEY") if sec else "CUGA_SECRET_KEY"
    key_b64 = os.environ.get(key_env)
    if not key_b64: return None
    try:    return Fernet(key_b64.encode())
    except Exception: return None        # malformed key == no backend, not a crash

# :124-134 — exact (agent, version) row first, then '*' agent fallback, same version;
# NOTE: there is NO version fallback — version must match exactly
if not row:
    if agent_id != "*":
        row = await store.fetchone(ph("... WHERE ... AND agent_id = '*' AND version = ? ..."), (...))

# :145-179 — sync bridge: NO running loop → asyncio.run; running loop → daemon thread
# with its own loop + 5s Event timeout (you CANNOT await from inside a running loop,
# and asyncio.run would raise; a plain thread call would deadlock on the caller's loop)
loop = asyncio.get_running_loop()          # RuntimeError if none
...
t = threading.Thread(target=run, daemon=True)   # run(): result[0] = asyncio.run(get_secret(...))
finished = done.wait(timeout=5.0)
if not finished: raise TimeoutError("get_secret_sync timed out after 5s")
```

**Flow:** every entry point calls `ensure_schema` first (idempotent CREATE TABLE IF NOT EXISTS + commit — cheap, keeps zero-migration boot). Reads require `_fernet()` or warn+return None (missing key can never yield plaintext or a crash); writes REQUIRE it (RuntimeError — refusing to persist ciphertext-unrecoverable secrets silently would be worse). Upsert via `ON CONFLICT DO UPDATE` keeping `created_at`, refreshing `updated_at`. All failures inside `get_secret` log debug and return None.
**Invariant:** (1) Plaintext NEVER touches disk — unencrypted operation means the backend doesn't exist, not that it stores clear text; this is why `available()` on the db backends IS `_fernet() is not None`. (2) The wildcard fallback is agent-level only and ordered AFTER the exact row so per-agent overrides win. (3) The thread-bridge timeout is 5s hard — Vault/network slowness upstream of this layer, not here; raising (vs returning None) distinguishes "backend too slow" from "secret absent". (4) Rowcount-based delete truth comes from `store._last_rowcount` which BOTH stores set (local via cursor.rowcount, prod by parsing asyncpg's status string).
**Probe:** No direct unit suite for secrets_store itself (needs the config relational store + key env); its behavior is pinned transitively through the seeding/resolver consumers — `src/cuga/backend/secrets/seed.py` imports `_fernet/get_secret/set_secret` directly, and `tests/unit/test_manage_secret_redaction.py` pins the redaction side of the API surface. Coverage caveat: encryption round-trip has no direct test at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "secrets_store get_secret set_secret get_secret_sync _fernet ensure_schema", limit: 10 });
```

## Verdict
Adopt the Fernet-or-nothing gate (reads degrade to None, writes refuse loudly), the composite PK with `'*'` agent fallback after exact match, ensure_schema-per-call idempotency, single-SQL dual-dialect placeholders, and the daemon-thread sync bridge with hard timeout. Adapt the key env var name, timeout value, and tags typing to your host. Omit the class-name-sniffing prod detection only if your Protocol carries an explicit dialect flag instead.
