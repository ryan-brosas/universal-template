<!-- capsule-v2 -->
# search_when_ready & error taxonomy — how do callers absorb indexing lag and classify failures?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does the package turn async ingestion + indexing lag + partial failures into a usable caller contract?

## verify.py / exceptions.py
**Path/Symbol:** `ingestion/src/zep_ingest/verify.py:23` (`search_when_ready`, DEFAULT_TIMEOUT_SECONDS=120, DEFAULT_POLL_SECONDS=5); `exceptions.py:18-70` (ZepIngestError hierarchy; BatchUnavailableError/InvalidBatchResponseError carry `partial_result`).
**Signature:** `search_when_ready(client, query, *, graph_id=None, user_id=None, scope="edges", limit=10, timeout=120.0, poll_interval=5.0, **search_kwargs) -> GraphSearchResults`.
**Data Shape:** Readiness = ANY of context/edges/nodes/episodes/observations/thread_summaries non-empty.

### Decisive source
```python
# verify.py docstring — the window every script hits:
# Ingestion is asynchronous end to end: even after ``IngestResult.wait()``
# reports success, just-written facts take a few more seconds to become
# searchable. ... it never raises on empty results, since "nothing matched"
# is a valid answer.

# exceptions.py philosophy:
# configuration errors and unusable API responses raise immediately;
# per-item runtime failures are collected into IngestResult.
# BatchUnavailableError.partial_result: "callers must not blindly re-submit
# everything when this is set."
```

**Flow:** wait() raises IngestTimeoutError (result stays usable) or IngestUntrackedError (no completion handle ⇒ outcome unknown-not-bad) → raise_for_status() opt-in strictness derives its failure set FROM the terminal sets → after wait(), search_when_ready polls graph.search until first non-empty response or deadline, returning the final empty response rather than raising → fallback warnings are insert(0)'d so the notice precedes stream warnings.
**Invariant:** "Untracked" ≠ failed: unknown outcome gets its own exception and stays excluded from raise_for_status. Partial-carrying exceptions exist so a fallback retry cannot duplicate already-submitted batches. Empty search is an answer, never an error.
**Probe:** `grep -c 'def test' ingestion/tests/test_verify.py ingestion/tests/test_exceptions.py | awk -F: '{s+=$2} END{print s}'` → ≥16.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "search_when_ready poll empty result untracked partial_result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt readiness-poll helper + untracked-as-unknown semantics + partial-result-carrying exceptions; adapt timeout defaults and status vocabularies to your backend; omit Zep client types.
