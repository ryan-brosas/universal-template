<!-- capsule-v2 -->
# Project identity with remote-hash self-heal — how does a per-directory mapping survive folder moves?

**Source:** mem0 Apache-2.0 `main@7e096155`; Codebase Memory `mem0`. **Question:** how should a cwd-keyed resource mapping keep working after the repo is renamed or moved, without user action?

## Connected graph-selected seam
**Path/Symbol:** `integrations/mem0-plugin/scripts/_project.py`: `resolve_project_id` (:21-73, self-heal at :39-51), `save_project_mapping` (:93-111), `_remote_hash_key` (:114-137), `_remote_url_to_slug` (:140-175).
**Signature:** `resolve_project_id(cwd=None) -> str`; `_remote_hash_key(cwd=None) -> str  # "remote:" + sha256(url)[:16]`; `save_project_mapping(cwd, project_id) -> None`.
**Data Shape:** ~/.mem0/project_map.json holds BOTH `cwd → id` and `remote:<hash> → id` keys.

### Decisive source
```python
remote_key = _remote_hash_key(cwd)          # remote:<sha256(origin-url)[:16]>
if remote_key:
    mapped = project_map.get(remote_key, "").strip()
    if mapped:
        # Self-heal: write the new CWD key so future lookups are fast
        project_map[cwd] = mapped
        try:
            with open(map_path, "w") as f:
                json.dump(project_map, f, indent=2)
        except OSError:
            pass
        return mapped
```

**Flow:** MEM0_PROJECT_ID env → map[cwd] → map[remote-hash] (+rewrite map[cwd]) → git origin slug (`git@host:owner/repo.git`→`owner-repo`; strips .git, https/http/ssh/git://, git@ incl. host aliases; first `:` becomes `/`) → basename(cwd) → "unknown". Branch: `git branch --show-current` else "unknown".
**Invariant:** the stable identity is the remote URL hash, not the path; self-heal rewrite is best-effort (OSError swallowed); slug collision risk accepted (owner-repo pair); save writes both keys so the NEXT move already has its fallback.
**Probe:** `cd $REFERENCE_ROOT/mem0 && .venv/bin/python -m pytest integrations/mem0-plugin/tests/test_project.py -q`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "resolve_project_id remote hash", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt dual-key (path + content-derived stable hash) maps with write-back self-heal for any cwd-scoped store; adapt the hash source (origin URL) to your stable identifier; omit git-specific slug rules if your ids come from elsewhere.
