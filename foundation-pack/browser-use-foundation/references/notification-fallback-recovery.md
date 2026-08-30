<!-- capsule-v2 -->
# Notification-fallback event recovery — when the response channel dies, how do you finish the run from live notifications?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** if the SDK response is missing/truncated or the transport errors mid-run, how does the wrapper decide to trust the notification stream instead — and what makes cancellation still produce a usable history?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — normalization `_sdk_notification_events` (:588, wraps payload-less events into `{seq,id,session_id,ts_ms,event_type,payload}`), identity dedupe `_dedupe_sdk_events` (:649) + `_sdk_event_dedupe_identity` (:677: seq+fingerprint → id → positional fallback), truncation marker `_sdk_events_truncated_for_transport` (:665), error-fragment classifier `_sdk_transport_error_after_final_result` (:669); decision site `Agent._run_sdk_agent` :5262-5277; cancel path `_preserve_sdk_notification_history` :5355.
**Signature:** `_dedupe_sdk_events(events) -> list` (first-seen order preserved; a later event with an id replaces an id-less twin).
**Data Shape:** notifications are the wire form `{method: 'agent.event'|'agent.projected_event', params.event…}`; projected events get `projected.`-prefixed kinds in summaries; response history arrives as `result.history.{events,child_events,usage_events,usage}`.

### Decisive source
```python
if notification_events and (
    not events                                    # empty/absent response body
    or _sdk_events_truncated_for_transport(events)   # explicit sdk.transport.truncated marker
    or len(notification_events) > len(events)        # stream saw MORE than survived serialization
    or (notification_result is not None and events_result is None)
):
    events = notification_events; child_events = []; usage_events = notification_events
    used_notification_events = True
...
if used_notification_events and events_result is not None:
    process_error = None          # recovered ⇒ transport failure no longer fails the run
# Cancellation preserves what already streamed:
except asyncio.CancelledError:
    await self._preserve_sdk_notification_history(sdk, started=started, process_error='CancelledError')
    await self._cancel_active_sdk_run(); raise     # client.close() cancels in-flight call
```

**Flow:** during `call()` every agent event is captured into `notifications` ring + queue regardless of the eventual response; on return, four-way test picks the richer source (response events win ties); usage falls back to `[events, child_events]`; the SDK's own `history.usage` becomes the sole usage event only if it exceeds the derived total (`_usage_tokens` compare :5296-5301). On CancelledError the same projection runs BEFORE the process is torn down so partial progress lands in `self.history`.
**Invariant:** the two channels describe the same log — cross-source dedupe by `(seq, type, payload-fingerprint)` must be stable whichever wins; a run that produced its final result before dying is SUCCESS despite stderr noise; cancelling never discards observed work (history first, then close).
**Probe:** `tests/ci/test_beta_agent.py:2962` recovers final from notifications after transport error, `:3008` nested-event normalization, `:3067` projected final events, `:3122` prefers notification final when response lacks result, `:3280` `test_beta_agent_preserves_sdk_notification_history_on_cancel`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_sdk_notification_events _dedupe_sdk_events _preserve_sdk_notification_history", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the richer-source arbitration (empty | truncated | longer | result-only-in-stream) plus preserve-history-on-cancel for any dual-channel (response + stream) agent bridge; adapt marker/fragment vocabularies; omit projected-event prefixing without a projection concept.
