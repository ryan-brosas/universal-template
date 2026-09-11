<!-- capsule-v2 -->
# Metadata store tolerance + restart recovery — why can a file-task row have NO status key, and what must happen to in-flight work at boot?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#683/#687); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The same `file_tasks_json` column crashed Postgres warmup with `KeyError: 'status'` for weeks while SQLite tolerated it — what is the shape contract, and how do both backends share one recovery rule?

## normalize_file_tasks + mark_file_tasks_interrupted
**Path/Symbol:** `src/cuga/backend/knowledge/metadata/base.py:10-79` (`INTERRUPTED_ERROR`, `_RECOVERABLE_FILE_STATUSES = ("pending", "processing")`, `normalize_file_tasks`, `mark_file_tasks_interrupted`); consumers `sqlite_store.py:186-190` and `postgres_store.py:209-216` (`recover_stale_tasks` bodies collapsed to shared helpers); profile-path hardening `knowledge/config.py:411-443` (`load_profile`: VALID_PROFILES gate + `child_path_under` join).
**Signature:** `normalize_file_tasks(raw: Any) -> dict[str, Any]`; `mark_file_tasks_interrupted(file_tasks: dict) -> dict` (in place).

### Decisive source
```python
# base.py:26-52 — the two on-disk shapes that broke backends differently
def normalize_file_tasks(raw):
    """Two shapes on disk make this necessary:
    1. **A file-task entry may legitimately have no ``status`` key.** The ingest
       worker's progress emits replace the whole entry with
       ``{filename, stage, progress}`` on purpose ... Any task killed mid-ingest
       therefore leaves a status-less entry behind. Readers must treat a missing
       status as *non-terminal*, never assume the key exists — assuming it
       crashed Postgres warmup with ``KeyError: 'status'`` (#683) while SQLite
       tolerated it, and the two backends silently diverged for weeks.
    2. **The payload may not be an object at all** — corrupt or truncated JSON,
       ``null``, or a list written by an older build. Returning ``{}`` keeps the
       caller's re-serialization from persisting a non-object back into a column
       the rest of the code reads as a mapping."""
    if isinstance(raw, (str, bytes, bytearray)):
        try: raw = json.loads(raw)
        except (TypeError, ValueError): return {}
    return raw if isinstance(raw, dict) else {}
```
```python
# base.py:58-74 — recovery defaults missing status to PENDING (recoverable)
def mark_file_tasks_interrupted(file_tasks):
    for ft in file_tasks.values():
        if not isinstance(ft, dict):
            continue
        if ft.get("status", "pending") in _RECOVERABLE_FILE_STATUSES:
            ft["status"] = "failed"
            ft["error"] = ft.get("error") or INTERRUPTED_ERROR   # keep specific error
    return file_tasks
```

**Flow:** every backend's `recover_stale_tasks` now reads `mark_file_tasks_interrupted(normalize_file_tasks(row["file_tasks_json"]))` — the tolerance rules live in ONE place instead of two drifting implementations; Postgres additionally fixed its UPDATE to bind `status` as a parameter (`?`-style positional) rather than interpolating the literal. Non-dict entries are skipped not dropped; an existing specific error beats the generic restart message. Companion hardening in the same drift: `load_profile` now rejects unknown names with ValueError BEFORE building any path and joins via `child_path_under` (refuses separators/`..`), closing the published-config path-traversal hole; the heavy import sits inside the function because it drags ~2800 modules / 1.6s.

**Invariant:** (1) Missing `status` ≠ terminal — the SAME convention governs three sites: `_blocks_reupload` (default "processing"), `_cancel_task_locked` (default non-terminal → mark cancelled/skipped), recovery (default "pending" → failed). A porter who "fixes" any of these to `.get("status") in TERMINAL` without a default reintroduces #683. (2) Corrupt/non-object payloads normalize to `{}` so callers never re-persist garbage into a mapping-typed column. (3) Restart recovery marks only NON-terminal entries failed — indexed/cancelled outcomes survive a restart untouched.

**Probe:** direct tests `tests/unit/test_knowledge_recover_stale_tasks.py` (status-less entries recovered, corrupt JSON tolerated, terminal statuses preserved — 251 lines); `tests/unit/test_knowledge_profile_paths.py::test_unknown_but_harmless_name_is_rejected` (:61) + traversal cases (:43/:69, file is 75 lines); backend-parity via `tests/unit/test_knowledge_routes.py`.

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "normalize_file_tasks mark_file_tasks_interrupted recover_stale_tasks load_profile", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT when a JSON blob column carries semi-structured records written by multiple code versions: normalize once centrally, default absent discriminator fields toward the SAFE interpretation (live/pending), and share the recovery rule across storage backends so they cannot diverge again.
