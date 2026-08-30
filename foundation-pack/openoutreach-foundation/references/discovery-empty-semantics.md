<!-- capsule-v2 -->
# Discovery empty-page semantics — when is an empty result a fact about the world vs your call?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** A search API returns an empty page for four different reasons — how do you tell them apart so you never permanently blacklist a good query?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/discover.py:_fetch` (:97-124), `_handle_empty` (:127-169), `discover` (:172-231); `openoutreach/discovery.py:Page` (:264-275), `search` (:277-309).
**Signature:** `search(filters, limit=100, offset=0) -> Page(leads: list[dict], leads_found: int | None)`; `_handle_empty(node, offset, page) -> str | None` (verdict or None = keep node).
**Data Shape:** `leads_found` is the provider's exact corpus count — **only meaningful at offset 0** (past any result-set end the API reports 0, at 10,100 for a huge query and at 500 for a 397-row one). `None` means "not asked at offset 0", never zero.

### Decisive source
```python
# _handle_empty:
if page.leads_found:                       # rows empty BUT count positive
    return None                            # transport artifact (burst answered a
                                           # 71M-lead query with an empty page in 0.0s)
if offset == 0:
    time.sleep(EMPTY_RETRY_DELAY_S)        # 5s spaced retry before believing a zero;
    retry = _fetch(node, 0)                # the retirement record prunes a whole subtree
    if retry is None or retry.leads or retry.leads_found:
        return None
# only now: select.retire(node, at_offset=offset)

# _fetch: a refusal is not an outage and is re-raised
except BetterContactUnavailable as exc:
    if exc.error_type != ErrorType.PROVIDER_UNAVAILABLE:
        raise                              # 401/402/429-exhausted must stop the job
    return None                            # outage: node keeps its frontier place
```

**Flow:** fetch → None (outage) ⇒ return 0, node stays → empty page → positive count ⇒ artifact, never retire → offset 0 ⇒ one spaced retry → still empty ⇒ retire with verdict dead/drained/capped.
**Invariant:** The old walk called `mark_exhausted` on ANY empty page — final, no retry — which is how one transport hiccup permanently retired a campaign's best query, and how "matches nobody" got written for queries with millions of matches. Nothing is retired on a first empty at offset 0 without a spaced retry agreeing. An unknown filter *value* yields a benign empty page (one fetch spent); an unknown filter *key* hands back the unfiltered page **with rows**, which reads as success — so keys are constrained in schemas (`Seniority` Literal), not trusted to the wire.
**Probe:** `tests/test_discovery.py::TestSearch` (:43-79), `tests/test_discovery_wiring.py::TestEmptyPages` (empty-page loop behavior incl. `test_the_loop_tries_the_next_node_after_a_dead_one` :180-189).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "discover", limit: 5 });
```

## Verdict
Adopt: carry the corpus count home and treat empty+positive-count as an artifact; spaced-retry before believing offset-0 zeros; refusals re-raised while outages keep state. Adapt the retry delay and verdict vocabulary; omit Lead Finder's specific `summary.leads_found` field name.
