<!-- capsule-v2 -->
# Checkpoint filename-encoded lineage — how do checkpoint files record their parent without opening the blob, and how are branches prevented from escaping the directory?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What naming scheme gives queryable lineage + branch isolation with plain filesystem tools?

## {ts}_{uuid8}_p-{parent}.json under branch subdirs
**Path/Symbol:** `lib/crewai/src/crewai/state/provider/json_provider.py` (`_build_path` :147–167, `_safe_branch` :22–33, `extract_id` :113–123, `prune` :98–111); lineage chain `state/runtime.py:216–227`.
**Signature:** `checkpoint(self, data: str, location: str, *, parent_id: str | None = None, branch: str = "main") -> str`.
**Data Shape:** `location/branch/{ts}_{short_uuid}_p-{parent_suffix}.json`; parent suffix literal `"none"` when root.

### Decisive source
```python
def _safe_branch(base: str, branch: str) -> None:
    base_resolved = str(Path(base).resolve())
    target_resolved = str((Path(base) / branch).resolve())
    if (
        not target_resolved.startswith(base_resolved + os.sep)
        and target_resolved != base_resolved
    ):
        raise ValueError(f"Branch name escapes checkpoint directory: {branch!r}")
```
```python
# extract_id — checkpoint id = timestamp+uuid prefix, parent stripped
idx = stem.find("_p-")
return stem[:idx] if idx != -1 else stem
```
```python
# runtime._chain_lineage — next write's parent is this write's id
self._checkpoint_id = provider.extract_id(location)
self._parent_id = self._checkpoint_id
```

**Flow:** write path built under validated branch subdir (resolve-based prefix check defeats `../` and absolute tricks; equality allows branch == base itself) → JSON blob written → provider returns path → runtime extracts id from the STEM and chains it as next write's parent → prune deletes oldest beyond max_keep PER BRANCH (`max_keep==0` wipes all), mtime-ordered.
**Invariant:** Lineage lives in FILENAMES: `ls | grep _p-` reconstructs chains without parsing 100MB blobs. Branch validation runs in BOTH `_build_path` and `prune` — a port validating only at write leaves prune open to traversal. The id is the prefix BEFORE `_p-`, so parent-bearing and root checkpoints share one id format.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_checkpoint.py::TestJsonProviderFork" "lib/crewai/tests/test_checkpoint.py::TestRuntimeStateLineage" -q` (expect 24 passed incl. branch-subdir storage, fork auto-naming, branch-aware prune).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "JsonProvider checkpoint branch filename parent prune extract_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt encoded-lineage filenames + resolve-prefix branch validation + per-branch pruning; adapt to object stores by moving lineage into keys/metadata; omit SQLite twin if you only need files. Direct tests executed green at pin.
