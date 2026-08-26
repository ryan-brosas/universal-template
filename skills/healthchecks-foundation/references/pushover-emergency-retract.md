<!-- capsule-v2 -->
# Pushover emergency-cancel ladder + Slackalike template family — priority-gated fan-out and one payload builder, many brands

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do priority-tiered push channels guarantee an emergency page is RETRACTED on recovery, and how do seven Slack-compatible integrations share one attachment payload without forking?

## po/transport.py: Pushover.is_noop/notify + slack/transport.py: Slackalike
**Path/Symbol:** `po/transport.py:is_noop` (:56-64), `notify` (:66-101), `raise_for_response` (:43-54), CANCEL_TMPL receipt cancel; `slack/transport.py:Slackalike.payload` (:28-84), `fix_asterisks` (:79-83), `Slack.raise_for_response` (:95-112); group composition `hc/integrations/group/transport.py:Group.notify` (:13-24).
**Signature:** `is_noop(status: str) -> bool` (per-channel up/down opt-outs); `payload(self, flip) -> JSONDict`; value grammar `"user_key|down_prio[|up_prio]"`.
**Data Shape:** Priority tiers: -3 disabled / 2 emergency (Pushover); emergency sends carry retry+expire params; tags=check.unique_key links cancels. SlackFields short/long typing; mrkdwn_in fields; body fenced only when no ``` present.

### Decisive source
```python
# po/transport.py — the recovery MUST reach the same device class that paged
if flip.new_status == "up" and down_prio == "2":
    url = self.CANCEL_TMPL % check.unique_key      # /receipts/cancel_by_tag/<unique_key>
    self.post(url, data={"token": settings.PUSHOVER_API_TOKEN})
...
# Emergency notification
if prio == "2":
    payload["retry"] = settings.PUSHOVER_EMERGENCY_RETRY_DELAY
    payload["expire"] = settings.PUSHOVER_EMERGENCY_EXPIRATION

# 400 user-invalid => permanent (channel is dead, stop retrying)
if doc.user == "invalid":
    message += " (invalid user)"
    permanent = True

# slackalike — Markdown-asterisk neutralization overridable per brand
def fix_asterisks(self, s):
    # base impl prepends Combining Grapheme Joiner characters but subclasses
    # can override this function and escape asterisks differently
    return s.replace("*", "\u034f*")
```

**Flow:** Pushover: value triple selects per-direction priority; is_noop maps prio -3 → skip BEFORE Notification rows exist; down-priority==2 arms the cancel-by-tag pre-send on recovery; emergency retries/expiration come from settings so ops tunes escalation windows. Group transport composes child channels via channel.notify(flip, is_test=is_test), counting non-"no-op" errors and raising a summarized TransportError — error strings as data make composition possible.
**Invariant:** The cancel call fires BEFORE the up notification and keys on check.unique_key (stable across renames), because Pushover dedupes by tag: skipping or reordering leaves a ringing phone with no resolution path. raise_for_response overrides are where each vendor's "this can never succeed" vocabulary becomes permanent=True — Slack's 404/invalid_token, Pushover's invalid user — protecting the shared 3-try budget from dead endpoints. last_ping body is included ONLY when the fence-free guard passes, keeping payloads renderable.
**Probe:** `hc/integrations/po/tests/test_notify.py::test_it_cancels_emergency_notification` (call order: cancel then up; title 🟢 Foo is UP), `test_it_supports_up_priority`, `hc/integrations/slack/tests/test_notify.py::test_it_handles_500`, `test_webhooks_handle_variable_variables` sibling in webhook suite, `hc/integrations/group/tests/test_notify.py::test_it_handles_partial_failure`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "pushover priority cancel slackalike payload", limit: 10 });
```

## Verdict
Adopt tag-keyed cancel-before-notify for any escalation-priority channel, per-brand raise_for_response permanent tables feeding ONE retry loop, and a single payload-builder base class for lookalike APIs. Adapt priorities/tiers and field layouts. Omit the CGJ asterisk trick in favor of your brand's escaping — but keep it behind an overridable seam exactly like fix_asterisks.
