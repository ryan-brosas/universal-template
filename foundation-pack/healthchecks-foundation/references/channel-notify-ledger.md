<!-- capsule-v2 -->
# Channel.notify ledger ladder — every send attempt writes a Notification row, success or fail

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does the notification dispatcher keep per-channel delivery state honest across concurrent flips, deleted channels, and permanent transport errors?

## Channel.transport / Channel.notify / Notification
**Path/Symbol:** `hc/api/models.py:Channel.transport` (:1135-1147), `notify` (:1149-1184), `Notification` (:1336-1350); test-notification driver `hc/front/views.py:send_test_notification` (:1302-1336).
**Signature:** `transport -> Transport` (lazy string→class import cached in TRANSPORTS dict); `notify(flip: Flip, is_test: bool = False) -> str`.
**Data Shape:** Return contract: "" (success) | "no-op" | human-readable error string. Channel columns updated post-send: `last_notify`, `last_notify_duration`, `last_error`, `disabled`. TRANSPORTS maps 28 kinds → ("Label", "dotted.path.Class") strings resolved on first use.
**Flow:** is_noop check short-circuits BEFORE creating any rows → build Notification with error="Sending" → IntegrityError on save means channel/check vanished concurrently: return "Channel or check does not exist any more" without raising → transport.notify(flip, notification=n) inside try → TransportError caught: error=e.message, disabled latches True only if e.permanent → two UPDATEs close the attempt (notification.error; channel's last_* + disabled) → return error string.

### Decisive source
```python
# hc/api/models.py — lazy transport resolution + the ledger update pair
label, cls = TRANSPORTS[self.kind]
# import transport classes on first use, and cache in TRANSPORTS
if isinstance(cls, str):
    modulename, classname = cls.rsplit(".", maxsplit=1)
    cls = getattr(import_module(modulename), classname)
    TRANSPORTS[self.kind] = (label, cls)
return cls(self)
...
try:
    self.transport.notify(flip, notification=n)
except transports.TransportError as e:
    disabled = True if e.permanent else disabled
    error = e.message

Notification.objects.filter(id=n.id).update(error=error)
Channel.objects.filter(id=self.id).update(
    last_notify=start,
    last_notify_duration=now() - start,
    last_error=error,
    disabled=disabled,
)
return error
```

**Invariant:** The Notification row exists BEFORE the send (status "Sending") so a crash mid-send leaves evidence, not silence; final state is written via filter().update() (not instance save) to avoid clobbering concurrent fields. Permanent errors are the ONLY thing that can flip disabled=True here — a transient timeout must never silently kill a channel. The error-string return contract (never raise past notify) is what lets group channels count partial failures and let the UI show "Could not send... <error>". Test notifications leave owner NULL and pass is_test=True so HttpTransport retry stays off. The dummy-Check trick (`Check(name="TEST", status="down", project=...)` unsaved) reuses the whole pipeline for previews — Flip.down_duration returns None for unsaved owners by design.
**Probe:** `hc/api/tests/test_channel_model.py` (webhook_spec mixed down/up), `hc/integrations/webhook/tests/test_notify.py::test_webhooks_handle_curl_errors` (error lands in n.error), `hc/api/tests/test_notify.py::test_it_handles_deleted_channel` (IntegrityError path returns exact string), `hc/front/tests/test_send_test_notification.py::test_it_handles_webhooks_with_no_down_url` (down no-op → retried as up-flip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "channel notify transport notification error", limit: 10 });
```
Resolves line-exact: Channel.notify :1149-1184.

## Verdict
Adopt write-ahead delivery rows, error-as-return-string dispatch, duration-sorted adaptive ordering input (Flip.select_channels), and permanent-only disabling. Adapt the transport registry format and your equivalent of IntegrityError-on-deleted-parent. Omit the dummy-check preview trick if you have a dedicated dry-run surface.
