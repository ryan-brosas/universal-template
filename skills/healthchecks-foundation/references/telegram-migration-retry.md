<!-- capsule-v2 -->
# Telegram migration-retry — error-payload chat_id migration with one-shot re-send

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** When a Telegram group migrates and the API answers "chat not found"-class errors with a migrate_to_chat_id parameter, how does the transport heal its stored credentials mid-flight instead of failing?

## telegram/transport.py: MigrationRequiredError / raise_for_response / notify
**Path/Symbol:** `hc/integrations/telegram/transport.py:MigrationRequiredError` (:13-17), `PERMANENT_ERRORS` tuple (:19-27), `ErrorModel/MigrationParameters` models (:29-36), `raise_for_response` (:38-58), `send` (:60-74, classmethod reused by front.views.telegram_bot), `notify` (:76-91); storage writer `hc/api/models.py:update_telegram_id` (:1281-1285).
**Signature:** `MigrationRequiredError(message, new_chat_id)` (permanent=True by construction); `send(cls, chat_id: int, thread_id: int | None, text: str)`; value JSON `{id, thread_id?, type?, name?}`.
**Data Shape:** Telegram 400 body → pydantic ErrorModel{description, parameters?{migrate_to_chat_id}}; PERMANENT_ERRORS is a literal string table (group deleted, bot blocked/kicked, user deactivated, chat not found).

### Decisive source
```python
# telegram/transport.py — classify, then let the payload redirect you
try:
    m = Telegram.ErrorModel.model_validate_json(response.content)
except ValidationError:
    raise TransportError(message)
if m.parameters:
    chat_id = m.parameters.migrate_to_chat_id
    raise MigrationRequiredError(m.description, chat_id)
...
# notify(): save-then-retry, exactly once
try:
    self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)
except MigrationRequiredError as e:
    # Save the new chat_id, then try sending again:
    self.channel.update_telegram_id(e.new_chat_id)
    self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)
```

**Flow:** Rate gate (TokenBucket.authorize_telegram) → render (body clipped at 1000 chars against a 4096 API ceiling for consistency with other transports) → send. Vendor error JSON is schema-validated BEFORE classification; description strings matching the permanent table set permanent=True so the shared retry budget aborts immediately on dead chats. A parameters.migrate_to_chat_id short-circuits everything: the exception CARRIES the new id, notify persists it via update_telegram_id (read-modify-write of the channel's JSON value), and re-sends synchronously.
**Invariant:** Migration is the ONE vendor error that mutates channel state from inside the send path — precisely because the new destination is authoritative in the same payload as the failure. The retry happens exactly once and only for this class; every other TransportError propagates to Channel.notify's ledger ladder. send() being a classmethod is deliberate: the signup bot flow (front.views.telegram_bot) shares it, so invite links and alert sends cannot drift in framing. Permanent-error strings are matched EXACTLY — upstream accepts the brittleness because false-permanent kills channels silently.
**Probe:** `hc/integrations/telegram/tests/test_notify.py::test_it_works`, migration pins via `test_it_handles_reason_failure` sibling asserts; `hc/front/tests/test_update_channel.py` (value rewrite round-trip), `hc/api/tests/test_channel_model.py::test_webhook_spec_handles_mixed` twin for JSON-value discipline.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "telegram migration chat_id permanent error", limit: 10 });
```

## Verdict
Adopt schema-first error classification with a carrying exception for credential-healing retries, exact-string permanent tables behind your own vocabulary, and shared classmethod send between interactive and delivery flows. Adapt to your vendor's redirect semantics. Omit thread_id/topic support if your target has no forum concept — but keep "heal-the-credential" errors separate from "give-up" errors at the TYPE level.
