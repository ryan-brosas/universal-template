<!-- capsule-v2 -->

# Content-hash SQLite cache with per-task pooled connections — Why does the cache DB stay tiny and how do concurrent async tasks share aiosqlite safely?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** Why does the cache DB stay tiny and how do concurrent async tasks share aiosqlite safely?

## Pool + hash offload + UPSERT

**Path/Symbol:** `crawl4ai/async_database.py:AsyncDatabaseManager.get_connection (101-207), acache_url (478-588), _store_content (641-654)`.

**Signature:** `@asynccontextmanager async def get_connection(self); content_hash = generate_content_hash(content); INSERT ... ON CONFLICT(url) DO UPDATE SET ...`.

**Data Shape:** Singleton `async_db_manager`. Table crawled_data(url PRIMARY KEY, ..., etag, last_modified, head_fingerprint, cached_at REAL). Content columns store HASHES; blobs live under ~/.crawl4ai/<content_type>/<hash>. Pool keyed by id(asyncio.current_task()), bounded by asyncio.Semaphore(pool_size=10).

### Decisive source
```python
await self.connection_semaphore.acquire()
        task_id = id(asyncio.current_task())
        ...
                    conn = await aiosqlite.connect(self.db_path, timeout=30.0)
                    await conn.execute("PRAGMA journal_mode = WAL")
                    await conn.execute("PRAGMA busy_timeout = 5000")
                    ... # PRAGMA table_info(crawled_data) must contain ALL expected columns
        finally:
            ...close conn, del from pool...
            self.connection_semaphore.release()

    async def _store_content(self, content: str, content_type: str) -> str:
        if not content:
            return ""
        content_hash = generate_content_hash(content)
        file_path = os.path.join(self.content_paths[content_type], content_hash)
        if not os.path.exists(file_path):
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
        return content_hash
```

**Flow:** get_connection lazily initializes (init_lock double-check) -> semaphore bounds concurrency -> per-task connection created ONCE and REUSED across operations within the task, closed in finally -> execute_with_retry wraps ops with linear backoff sleep(1*(attempt+1)) up to max_retries=3 -> writes UPSERT all columns incl. validation metadata; etag/last-modified pulled case-insensitively from response_headers; markdown serialized via model_dump_json regardless of str/StringCompatibleMarkdown/MarkdownGenerationResult input shape -> reads rehydrate hashes via _load_content, JSON-parse media/links/metadata, and RESCUE legacy plain-string markdown rows into MarkdownGenerationResult(raw_markdown=...).

**Invariant:** (1) Every pooled connection asserts the FULL expected column set at creation - a stale/pre-migration DB fails fast instead of corrupting reads. (2) Empty content stores hash '' and load returns None->'' - never write empty files. (3) The pool is keyed by TASK id, not call site: two awaits in the same task share one connection, so nested get_connection within a task is safe; cross-task sharing never happens. (4) VersionManager gates update_db_schema+migrations to version bumps only.

**Probe:** `tests/cache_validation/test_end_to_end.py` (round-trips results through async_db_manager incl. revalidation metadata)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "acache_url aget_cached_url connection pool", "limit": 5}'
```

## Verdict
Adopt the row-points-to-hash-file layout and the task-id connection pool with its schema assertion. Adapt pool sizing and the DB path env var. Omit the markdown four-shape normalization only if your host guarantees one writer type - the read-side rescue exists precisely because writers historically varied.
