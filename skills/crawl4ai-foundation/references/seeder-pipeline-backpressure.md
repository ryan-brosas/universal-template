<!-- capsule-v2 -->

# Seeder fan-out: bounded queue, QPS semaphore, cooperative early-stop — How do you validate tens of thousands of discovered URLs concurrently with a hard hits/sec cap AND a max_urls cut-off that leaves no hung workers?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** How do you validate tens of thousands of discovered URLs concurrently with a hard hits/sec cap AND a max_urls cut-off that leaves no hung workers?

## Producer/workers with drain-flush termination

**Path/Symbol:** `crawl4ai/async_url_seeder.py:AsyncUrlSeeder.urls (364-555)`.

**Signature:** `queue = asyncio.Queue(maxsize=min(10000, max(1000, concurrency * 100))); workers = [asyncio.create_task(worker(results)) for _ in range(concurrency)]`.

**Data Shape:** Shared mutable `results` list appended by workers (single event loop -> safe). stop_event halts producer AND workers; producer_done gates worker exit; _rate_sem = Semaphore(hits_per_sec) throttles _validate globally.

### Decisive source
```python
if max_urls > 0 and len(res_list) >= max_urls:
                    stop_event.set()
                    queue.task_done()
                    # flush whatever is still sitting in the queue so
                    # queue.join() can finish cleanly
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                            queue.task_done()
                        except asyncio.QueueEmpty:
                            break
                    break
```

**Flow:** producer streams sitemap+CC generators through a seen-set deduper into the bounded queue (put blocks -> backpressure upstream) until sources exhaust or stop_event fires -> workers loop: wait_for(get, 5) -> check max_urls (set stop_event, task_done, DRAIN-FLUSH remainder, break) -> optionally acquire global rate semaphore -> _validate appends -> task_done -> main gathers producer+workers THEN queue.join() -> optional collective BM25 pass scores ALL heads against the query at once (min-max normalize; all-equal->0.5) -> threshold-filter -> sort desc -> slice max_urls.

**Invariant:** (1) Every queue item must receive exactly one task_done across BOTH the normal and cut-off paths - missing one deadlocks queue.join(). (2) The rate semaphore wraps the WHOLE validate (HEAD + head fetch) so hits/sec counts validations, not individual sockets. (3) Worker exit condition is `queue.empty() and producer_done.is_set()` polled via wait_for timeouts - never a bare get() that could hang past producer death. (4) UnicodeEncodeError on enqueue is swallowed per-item (Windows paths) rather than killing the producer. (5) close() only acloses the client the seeder OWNS (_owns_client tracks injection).

**Probe:** `tests/test_issue_1213_bm25_dedup.py` (BM25 + dedup) + `tests/unit/` seeder units (queue/stop-event mechanics)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "AsyncUrlSeeder urls worker producer queue", "limit": 5}'
```

## Verdict
Adopt the bounded-queue + stop_event + drain-flush shutdown trio; the queue_size formula and worker-exit protocol are what let this scale to hundreds of thousands of URLs without RAM spikes or hangs. Adapt the validation body. Omit the BM25 machinery if you don't need relevance ranking - it degrades gracefully when rank_bm25 is absent (warn + return unranked).
