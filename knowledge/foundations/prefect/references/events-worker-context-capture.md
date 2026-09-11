<!-- capsule-v2 -->

# EventsWorker context capture at send time — How do you enrich queued events with the EMITTER'S context later, on the worker loop?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** When event enrichment needs contextvars that only exist at emit time but resolution happens asynchronously later, how do you pair snapshots with queue items without leaks?

## copy_context keyed by event id; drop hook pops it; handle re-enters it before enrichment

**Path/Symbol:** `src/prefect/events/worker.py:EventsWorker (64-165)` — `__init__ (69-80)`, `_prepare_item (92-93)`, `_on_item_dropped (96-97)`, `_handle (99-104)`, `attach_related_resources_from_context (106-118)`, client ladder `instance (130-165)`; tests `tests/events/client/test_events_worker.py`, `tests/events/client/test_bounded_queue.py`.

**Signature:** `EventsWorker(QueueService[Event])`; `__init__(self, client_type, client_options)` sets `self._max_queue_size = get_current_settings().events.worker_max_queue_size` BEFORE `super().__init__()`.

**Data Shape:** `_context_cache: Dict[UUID, Context]` — one frozen contextvars snapshot per in-flight event.

### Decisive source
```python
def _prepare_item(self, event: Event) -> Event:
    self._context_cache[event.id] = copy_context()
    return event

def _on_item_dropped(self, item: Event) -> None:
    self._context_cache.pop(item.id, None)

async def _handle(self, event: Event):
    context = self._context_cache.pop(event.id)
    with temporary_context(context=context):
        await self.attach_related_resources_from_context(event)
    await self._client.emit(event)

async def attach_related_resources_from_context(self, event):
    if "prefect.resource.lineage-group" in event.resource:
        return   # lineage events attach their own (downstream-aware) related
    exclude = {r.id for r in event.involved_resources}
    event.related += await related_resources_from_run_context(
        client=self._orchestration_client, exclude=exclude)
```

**Flow:** send-side (`_prepare_item`, running in the emitter's thread/context) freezes `copy_context()` keyed by the event's UUID; if the bounded queue is full the item is dropped and its snapshot popped (no leak). Worker-side (`_handle`) pops the snapshot and re-enters it via `temporary_context` so run-context lookups see the EMITTER'S identity, then appends related resources (excluding resources already involved in the event) and emits. Client selection at `instance()`: Cloud-prefixed URL → PrefectCloudEventsClient(api_url, api_key); any URL → PrefectEventsClient; no URL + ephemeral allowed → start a SubprocessASGIServer and use its URL; else NullEventsClient. `set_client_override` swaps the selection for tests/DI.

**Invariant:** (1) Snapshot must be taken at SEND time — by handle-time the emitter's contextvars are gone; keying by event.id makes snapshot↔item pairing survive queue reordering. (2) Every cache insert must have exactly one pop path: handle-pop or drop-pop; a third exit (service crash) is acceptable leakage only because instances are fork/exit-reset anyway. (3) Instance-attribute `_max_queue_size` must be set BEFORE super().__init__ builds the Queue — the class attribute stays untouched (test-pinned).

**Probe:** direct tests `tests/events/client/test_events_worker.py:96 test_includes_related_resources_from_run_context` (related gains flow-run + flow roles), `:132 test_does_not_include_related_resources_from_run_context_for_lineage_events` (lineage ⇒ related == []), `:71 test_worker_instance_uses_client_override`, `tests/events/client/test_bounded_queue.py:88 test_max_queue_size_is_instance_attribute`, `:102-140 TestEventsWorkerOnItemDropped`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(EventsWorker|should_emit_events|emit_events_to_cloud)$", "limit": 5}'
```
(observed rank-1..3 all resolve into `src/prefect/events/worker.py` lines 29-165)

## Verdict
Adopt send-time context snapshots keyed by item id with symmetric pop-on-handle/pop-on-drop for deferred enrichment; adapt the settings-driven bounded size; omit the ephemeral-server bootstrap branch when your host always has an API URL.
