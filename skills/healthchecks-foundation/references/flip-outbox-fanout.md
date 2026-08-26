<!-- capsule-v2 -->
# Flip outbox — how do you decouple "status changed" from "notifications sent" using plain rows?

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks` (re-pinned pass 2 from retired `ext-healthchecks`, same HEAD). **Question:** What makes a Flip row a safe unit of work for fan-out, and which transitions must never page anyone?

## Flip model + select_channels
**Path/Symbol:** `hc/api/models.py:Flip` (:1358-1431), `create_flip` (:651-671), `hc/api/models.py:Check.create_flip` callers in `views.pause`/`resume`, partial index `api_flip_not_processed` (:1366-1380).
**Signature:** `select_channels() -> list[Channel]`; `create_flip(new_status: str, reason: str = "", mark_as_processed: bool = False) -> None`.
**Data Shape:** Columns: `owner FK`, `created` (backdated flip time), `processed: datetime | null` (the claim column), `old_status/new_status ∈ {up,down,new,paused}`, `reason ∈ {"", timeout, fail}`. Indexes: condition index on `processed IS NULL` for the worker, `(owner, created)` for statistics.

### Decisive source
```python
# hc/api/models.py — the fan-out selector
# Don't send alerts on new->up and paused->up transitions
if self.new_status == "up" and self.old_status in ("new", "paused"):
    return []

if self.new_status not in ("up", "down"):
    raise NotImplementedError(f"Unexpected status: {self.new_status}")

q = self.owner.channel_set.exclude(disabled=True)
q = q.order_by(F("last_notify_duration").asc(nulls_last=True))
return [ch for ch in q if not ch.transport.is_noop(self.new_status)]
```

**Flow:** Web processes create Flips (pause/resume pass `mark_as_processed=True` because there is nothing to notify; ping() creates up/down flips unprocessed). The separate sendalerts process claims unprocessed flips (`filter(processed=None).first()` then conditional `update(processed=now())`), calls select_channels, notifies each channel, and records dwell/send timings. The same rows double as downtime-statistics input (Check.downtimes_by_boundary replays them).
**Invariant:** new→up and paused→up are NON-EVENTS by contract — first-ever ping and manual resume must not page the on-call. Channel order is adaptive: fastest-confirmed channel first via `last_notify_duration` ascending with NULLs last, so a dead webhook can't delay the SMS that follows it. The dual use as notification outbox AND statistics ledger means you may never hard-delete flips casually — prune keeps ~93 days (see prune capsule).
**Deepening (pass 2, source re-verified at pin):** `Flip.down_duration` is a **`@cached_property`** (`hc/api/models.py:1415-1431`) — graph metadata renders it as a plain method, so trust source over snippets here. It asserts `old_status == "down"` (asking a going-down flip for downtime is a programming error), returns None for unsaved owners (the test-notification dummy-check path), and yields `created − prev_down_flip.created` ONLY when the immediately-previous flip is itself a down-flip — an outage older than the retained flip chain stays open-ended (None). Also sharpened: `views.resume` creates Flip("new"), not Flip("up") (see manual-transition-gate) — so the silenced paused→up arm is reachable only via direct status writes, while resumed checks get silenced later at their first real ping's new→up transition.
**Probe:** `hc/api/tests/test_flip_model.py::test_send_alerts_handles_new_up_transition` ([]), `test_it_skips_disabled_channels`, `test_select_channels_handles_noop` (email up:false/down:false → is_noop), `test_it_sorts_channels_by_last_notify_duration` ([c1, c9, default]), `test_down_duration_handles_unsaved_check`, `test_down_duration_checks_prev_flips_status` (:83-93, prev flip not down ⇒ None).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "flip select_channels notify processed", limit: 10 });
```
Resolves line-exact: Flip.select_channels :1388-1406.

## Verdict
Adopt the Flip-as-outbox row shape, the claim-by-conditional-update protocol, the two silent transitions, and duration-sorted fan-out. Adapt status vocabulary and reason codes to your domain. Omit the statistics dual-use only if you keep an equivalent event log elsewhere — deleting processed flips outright silently destroys your uptime history.
