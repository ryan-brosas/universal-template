<!-- capsule-v2 -->
# Local identity bootstrap — how does ~/.mem0/config.json carry telemetry identity across OSS and CLI surfaces without ever failing the host app?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** how is a per-install anonymous identity created, persisted atomically, and aliased to a real email exactly once — with zero exceptions leaking into library consumers?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/setup.py`: module boot (:8-14, `VECTOR_ID` uuid + `MEM0_DIR` override + makedirs at IMPORT time), `_load_config` (:21-32), `_write_config` (:35-53), `setup_config` (:56-68), `get_user_id` (:71-75), `read_anon_ids` (:78-93), `_alias_pair_marker`/`is_aliased`/`mark_aliased` (:96-131), `get_or_create_user_id` (:134-166). Consumers: `main.py :50` imports `setup_config()` and CALLS IT AT MODULE LEVEL (:459), `telemetry.py get_or_create_user_id`, `notices.py _load/_write_config`, `client/main.py :37` boot + `_maybe_alias_anon_to_email` (:56-79).
**Signature:** `_load_config() -> dict` ({} on missing/malformed); `_write_config(config) -> None` (never raises); `mark_aliased(anon_id, email)`; `get_or_create_user_id(vector_store=None) -> str`.
**Data Shape:** config.json: `{user_id: uuid4, telemetry?: {anonymous_id?: str, aliased_pairs?: [sha256_hex]}}`; alias marker = `sha256(f"{anon_id}\0{email}")` — NUL-separated domain-separation hash, email never stored in plaintext.

### Decisive source
```python
def _write_config(config):
    """Best-effort write of ~/.mem0/config.json. Never raises."""
    path = _config_path()
    temp_path = None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(path), delete=False) as f:
            temp_path = f.name
            json.dump(config, f, indent=4)
            f.flush(); os.fsync(f.fileno())       # durability BEFORE the atomic swap
        os.replace(temp_path, path)               # same-dir rename = atomic on POSIX
    except Exception:
        if temp_path:
            try: os.unlink(temp_path)             # no temp litter after failure
            except OSError: pass
        _logger.debug("Failed to write mem0 config %s: %s", path, e)
```
```python
def mark_aliased(anon_id, email):
    ...
    marker = sha256(f"{anon_id}\0{email}".encode("utf-8")).hexdigest()
    if marker not in aliased_pairs:               # read-modify-writeback of ONLY the telemetry key
        aliased_pairs.append(marker)
    telemetry["aliased_pairs"] = aliased_pairs; config["telemetry"] = telemetry
    _write_config(config)                         # fires $identify once per pair, ever
```

**Flow:** import-time `setup_config()` backfills top-level `user_id` when only the CLI's `telemetry.anonymous_id` exists (the documented CLI/OSS coexistence gap — without it OSS telemetry silently drops because `get_user_id()` returns None) → every later read re-loads from disk (no cache; multi-process safe-ish via last-writer-wins) → client surface, when it learns a user email, walks anon ids, skips already-aliased pairs via the hashed marker set, fires identify, and marks the pair → `get_or_create_user_id(vector_store)` additionally pins the identity INTO the store as a `{user_id, type: user_identity}` vector so dashboards can attribute installs.
**Invariant:** EVERY disk touch is fail-open (`except Exception → {} / debug-log`) — a read-only HOME degrades telemetry to "anonymous_user" but never breaks memory operations; writes are temp-file + fsync + `os.replace` so a crash mid-write can never truncate the config; aliasing is idempotent-by-hash so `$identify` fires once per (anon_id, email) even across processes; the two-surface ID scheme (top-level `user_id` vs nested `telemetry.anonymous_id`) must BOTH be understood or a port reads the wrong identifier.
**Probe:** `tests/test_telemetry_aliasing.py` (stubs `_write_config` :30-33 and exercises the alias ladder); consumer coverage via `tests/memory/test_notices.py` + `tests/memory/test_performance_slow_query_notice.py` which drive the shared config file. No dedicated suite for the atomic-write path itself — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "get_or_create_user_id _write_config aliased_pairs", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.memory.setup.get_or_create_user_id Function mem0/memory/setup.py 134-166)

## Verdict
Adopt the atomic best-effort write + hashed once-only alias markers for any local-first SDK identity; adapt the storage location/format; omit the vector-store pinning branch if your platform has real install attribution.
