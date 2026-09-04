<!-- capsule-v2 -->
|# Silent-batch recovery fetch — when a batched IN-query helper swallows errors and returns [], how do you keep one bad batch from silently deleting citations?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** A batch helper's failure is indistinguishable from "no rows" — where does recovery hook in so a lost batch degrades to per-id reads instead of missing metadata?

## Dedup → chunked IN-queries → diff requested-vs-returned → per-id gather with return_exceptions
**Path/Symbol:** `backend/python/app/modules/retrieval/retrieval_service.py` nested `async def _fetch_by_ids(record_ids, collection, label)` (L529–580, inside `search_with_filters`); fan-out via `fetch_files()/fetch_mails()/fetch_locations()` gathered concurrently L624–630.
**Signature:** `_fetch_by_ids(ids: list[str], collection: str, label: str) -> dict[id, node]`.
**Data Shape:** chunk size = imported constant `GRAPH_BATCH_CHUNK_SIZE`; resolved map keyed by `node["id"] or node["_key"]`; per-record enrichment needs `webUrl`/`mimeType` from the FILES/MAILS collections.

### Decisive source
```python
unique_ids = list(dict.fromkeys(record_ids))       # order-preserving dedup:
                                                   # a record matched by many chunks
                                                   # was once fetched once PER CHUNK
for start in range(0, len(unique_ids), GRAPH_BATCH_CHUNK_SIZE):
    nodes.extend(await self.graph_provider.get_nodes_by_field_in(
        collection, "id", unique_ids[start:start + GRAPH_BATCH_CHUNK_SIZE]) or [])
except Exception as e:
    self.logger.warning(f"Failed to batch fetch {label}, per-id fallback: {e}")
    nodes = []
...
# "Losing the batch strips webUrl/mimeType from every record in it, and a result
#  without mimeType is dropped outright by the required_fields filter below --
#  the citation disappears from the answer with no error. The except above
#  cannot catch that: get_nodes_by_field_in swallows its own errors and returns
#  [], so a failure looks exactly like 'no rows'. Recover on which ids actually
#  came back instead."
missing = [rid for rid in unique_ids if rid not in resolved]
if missing:
    per_id = await asyncio.gather(*[self.graph_provider.get_document(rid, collection)
                                    for rid in missing], return_exceptions=True)
    resolved.update({rid: doc for rid, doc in zip(missing, per_id)
                     if doc and not isinstance(doc, BaseException)})
```
(L537–579.)

**Flow:** collect file/mail ids per search result during metadata enrichment → one concurrent gather of files+mails+locations → each leg dedups, chunks into IN-queries, indexes by id → DIFF against what was requested (catches both raised errors AND silent empty batches) → concurrent per-id fallback; exception results filtered out.
**Invariant:** (1) Recovery keys on RETURNED ids, never on whether the call raised — a swallow-errors helper makes exceptions and empty sets look identical, so only the diff can tell them apart. (2) Per-id fallback failures are contained (`return_exceptions=True` + BaseException filter); they degrade to missing mimeType ⇒ that citation is later dropped by required_fields — bounded loss, not a failed request. (3) Order-preserving dict.fromkeys dedup keeps IN-clauses minimal AND stable for tests asserting exact call args (:1326–1328). (4) The three legs run as ONE asyncio.gather — locations soft-fail independently of files/mails.
**Probe:** EXECUTED at pin: combined battery 124 passed rc=0 (/tmp/psh21venv). Decisive tests: test_record_matched_by_many_chunks_is_fetched_once :1289–1328 (5 chunks ⇒ get_nodes_by_field_in called ONCE with ["rec1"]), test_fetch_files_exception_returns_empty_map :1255–1286 (raised batch error stays graceful), test_batch_file_and_mail_fetching :981–1000+, test_missing_mimetype_file_record_fetches_file :816–858 (asserts exact single FILES call + recovered mimeType/webUrl), gmail template variant :861–903. Anchor greps verified pre-write: GRAPH_BATCH_CHUNK_SIZE :39/:540/:543.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*modules/retrieval/*` query="_fetch_by_ids get_nodes_by_field_in batch fetch files mails fallback" → resolves the four decisive test classes.

## Verdict
Adopt the diff-based recovery whenever any bulk-read helper can fail open with an empty result; adopt chunk+dedup+concurrent-legs as the surrounding shape. Adapt chunk size and id-key extraction to your store. Omit the per-id fallback ONLY if your batch helper raises instead of swallowing — then a plain try/except suffices and the diff is dead weight.
