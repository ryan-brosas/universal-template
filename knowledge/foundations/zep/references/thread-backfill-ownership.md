<!-- capsule-v2 -->
# Thread backfill ownership — how do chat histories land on the right user's graph without cross-user writes?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** What must ingest_thread_messages verify about users and threads before submitting, and how are oversize messages handled?

## threads.py preflight
**Path/Symbol:** `ingestion/src/zep_ingest/threads.py:64` (`MAX_MESSAGE_CHARS = 4096`), `:65` (`_SPLIT_TARGET = 4000`), `:71` (`ThreadMessage`), `:106` (`_validate_ignore_roles`), `:136` (`_prepare`), `:155` (`_ensure_user_and_threads`).
**Signature:** `_ensure_user_and_threads(client, user_id, messages) -> None` raises ConfigurationError for missing user or foreign thread; thread.create "already exists" (409, or 400 with body text) tolerated.
**Data Shape:** ThreadMessage REQUIRES role/name/created_at ("a backfill should carry each turn's speaker type, speaker name, and original timestamp"); roles ∈ {user, assistant, system, function, tool, norole}.

### Decisive source
```python
# The API reports an existing thread as 400 "already exists" (or 409); any
# other 400 is a real validation error and must surface.
already_exists = error.status_code == 409 or (
    error.status_code == 400 and "already exists" in str(error.body))
if not already_exists: raise
# Thread IDs are project-global. A collision must be verified before adding
# messages; otherwise this import could CROSS A USER BOUNDARY and write into
# another user's conversation.
existing = client.thread.get(message.thread_id, lastn=1)
owner_id = getattr(existing, "user_id", None)
if owner_id != user_id:
    raise ConfigurationError(f"Thread {message.thread_id!r} already belongs to
        user {owner}; refusing to ingest it for {user_id!r}.")
```

**Flow:** require user_id → validate ignore_roles against documented set (bare string rejected; dedup order-preserving; empty→None so field is omitted) → materialize JSONL/array/object path or iterable → apply thread_id_suffix for namespacing re-runs → `_prepare`: content >4096 split at sentence boundaries via split_text at 4,000 target WITH count warning → user.get must exist ("a bare auto-created user would skip the profile and per-user setup") → create each distinct missing thread → submit batch/sequential/auto (auto fallback refuses when partial batches already submitted — re-submitting sequentially would duplicate them).
**Invariant:** Users are caller-owned (never auto-created); threads are backfill-owned containers (created if missing). Global thread-id collisions MUST be ownership-verified before writing. Sequential path groups by thread preserving per-thread chronological order.
**Probe:** `grep -c 'def test' ingestion/tests/test_threads.py` → 52 incl. `test_existing_thread_for_another_user_is_rejected` (match="already belongs"), `test_oversize_content_split_with_warning`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "ingest_thread_messages ensure user threads conflict owner", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt user-must-exist + thread-ownership verification + sentence-boundary message splitting; adapt role vocabulary and suffix strategy to your host; omit Zep batch item shapes.
