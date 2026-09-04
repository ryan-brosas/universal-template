<!-- capsule-v2 -->
# Auto-import triple dedup — how do you import project files idempotently when local hash state AND server state can both drift?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** a background importer re-runs every session start; local hashes say "unchanged" but the server may have lost the memories (or vice versa). What dedup ladder survives both drift directions?

## Hash-store + server-probe importer (auto_import.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/auto_import.py:main` (lines 262–366) + `_acquire_lock` (54–72) + `already_imported` (121–152) + `_delete_stale_chunks` (155–196); wired by `scripts/on_session_start.sh` line ~186 (`MEM0_CWD=... python3 auto_import.py 2>/dev/null &`).
**Signature:** `main() -> None`; `_acquire_lock() -> bool`; `already_imported(api_key, user_id, project_id, filename) -> bool`; `post_memory(api_key, content, user_id, filename, project_id, branch="") -> bool`.
**Data Shape:** `TARGET_FILES = ["CLAUDE.md", "AGENTS.md", ".cursorrules", ".windsurfrules", "mem0.md"]`; `MAX_FILE_SIZE = 100_000`; hash key `"{project_id}:{branch}:{filename}"` (branch omitted when empty); hash store `~/.mem0/file_hashes.json`; lock `~/.mem0/auto_import.lock` with 120s stale reclaim; chunks named `"{filename}[{i}/{n}]"` when n>1; metadata `{type:"project_profile", file:chunk_name, source:"auto-import"}`, `infer=False`.

### Decisive source
```python
        hash_key = f"{project_id}:{branch}:{filename}" if branch else f"{project_id}:{filename}"
        if hashes.get(hash_key) == current_hash:
            if already_imported(api_key, user_id, project_id, filename):
                log.debug("Unchanged and still in mem0, skipping: %s", filename)
                continue
            log.info("Hash matches but memories missing server-side, re-importing: %s", filename)
        elif already_imported(api_key, user_id, project_id, filename):
            log.debug("Already in mem0, updating hash store: %s", filename)
            hashes[hash_key] = current_hash
            updated = True
            continue
```
**Flow:** SessionStart(startup) backgrounds the importer → O_EXCL lock (stale >120s unlinked and retried; failure ⇒ skip run) → identity resolved, `save_project_mapping` persisted → search dirs = cwd + git root (when different) → per target file: pick first existing, realpath, size ≤ 100KB, SHA-256, skip in-run duplicate content via `seen_content_hashes` set → THE LADDER: hash-match + server-probe-pass ⇒ skip; hash-match + server-missing ⇒ re-import; hash-differs + server-has ⇒ adopt hash (server copy is current) and skip; hash-differs + server-missing ⇒ import. Import = delete stale chunks first (search top-20 by filename with `metadata.source=auto-import` filter, DELETE each `/v1/memories/{id}/`), chunk via `_chunking` (markdown → `split_by_headers`, else whole file; `filter_and_truncate` drops <50 chars, truncates >10000; empty result falls back to `content[:10000]`), POST each chunk with `infer=False`, and only on full success persist the new hash.
**Invariant:** the hash store is a CACHE, not the source of truth — the server probe is checked whenever the cache would allow a skip, in BOTH directions (cache-fresh/server-stale re-imports; cache-stale/server-fresh adopts). `infer=False` is mandatory for verbatim config text: these are human-authored project files, so role="user" is correct here (the opposite of the capture hooks — test_message_roles.py pins the boundary). Chunks carry the `file[i/n]` naming so `already_imported`'s prefix match (`filename` or `filename[`) recognizes multi-chunk imports. Hash persists only after ALL chunks succeed, so a partial import retries whole.
**Probe:** no dedicated test file for auto_import.py (honest gap); the chunking rungs ARE directly tested in `tests/test_import_competing_tools.py` (split_by_headers preamble+sections, filter_and_truncate 50/10000 boundaries — executed GREEN this pass, 13 passed). Byte-exact grep probes: `O_CREAT | os.O_EXCL` (1 hit), `file_hashes.json` (2 hits), `seen_content_hashes` (3 hits), `Hash matches but memories missing server-side` (1 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "auto import hash store already imported stale chunks", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions; MCP not connected this pass (DEGRADED path, whole-file direct reads + executed chunking tests instead).

## Verdict
Adopt the two-directional dedup ladder (local cache never trusted alone; server probe arbitrates both drift directions) and the delete-then-rechunk re-import for any declarative-file importer. Adapt target files, 100KB cap, and the 120s lock TTL to your host. Omit the mem0 endpoint/auth shape. Coverage: whole file read (374 lines); chunking helpers covered by executed direct tests; no dedicated auto_import test file (recorded gap).
