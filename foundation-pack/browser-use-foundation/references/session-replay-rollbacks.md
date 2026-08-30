<!-- capsule-v2 -->
# Compaction/rollback event replay — how do you apply undo and compaction markers to a linear event log before projecting it?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** when the terminal core emits `session.rollback {num_turns}` and `session.compacted {replay_from_seq}`, how does the Python side derive which events actually happened?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — `_events_after_terminal_rollbacks` (:1591), `_rollback_last_terminal_user_turn` (:1579), `_events_after_terminal_compaction` (:1559), `_compaction_replay_start_seq` (:1550); turn-classification helpers `_event_seq` (:1505), `_is_terminal_user_turn_event` (:1525), `_contextual_event_targets_turn` (:1535), `_rollback_turn_count` (:1515). Applied at the single entry `_history_from_events` :4006 `events = _events_after_terminal_rollbacks(_events_after_terminal_compaction(events))`.
**Signature:** `_events_after_terminal_compaction(events) -> list`; `_events_after_terminal_rollbacks(events) -> list`; `_rollback_last_terminal_user_turn(events) -> bool` (mutates in place).
**Data Shape:** rollback payload keys tried: `num_turns|turns|n` (default 1, bools skipped); compaction payload key `replay_from_seq` (int; a bool is rejected) else falls back to the compaction event's own seq.

### Decisive source
```python
# terminal user turns that can be undone:
if etype in ('session.input','session.followup'): return True
if etype in ('agent.message','agent.mailbox_input'):
    return isinstance(content,str) and content.strip() != ''
# undo = delete the user turn AND every contextual event attached to it:
target_seq = _event_seq(events[user_pos])
truncate_at = user_pos
while truncate_at > 0 and _contextual_event_targets_turn(events[truncate_at-1], target_seq):
    truncate_at -= 1          # workspace.context / model.*_context with before_seq == target
del events[truncate_at:]
# compaction replay boundary — events WITHOUT seq survive only if after the marker:
for index, event in enumerate(events):
    seq = _event_seq(event)
    if seq is not None:
        if seq > replay_start_seq: replay_events.append(event)
    elif index > compaction_index:
        replay_events.append(event)
```

**Flow:** first fold ALL `session.compacted` markers (last one wins via reverse scan): drop everything up to and including the marker, then keep events with `seq > replay_from_seq` (seq-less events kept only if they sit after the marker index); then process `session.rollback` markers IN ORDER against the partially-folded log, each deleting the last N terminal user turns plus their context attachments; only then run result/failure extraction on the folded log.
**Invariant:** rollback deletes context events by `before_seq` linkage so orphaned context never survives; an undo that finds no user turn is a no-op (`break` out of the count loop) rather than an error; compaction without `replay_from_seq` truncates at the marker instead of guessing a boundary; ordering (compaction → rollbacks) is fixed because a compaction boundary re-bases the seq space the rollbacks reason over.
**Probe:** `tests/ci/test_beta_agent.py:1367` `test_rust_history_applies_terminal_session_rollback` (2 steps remain, rolled-back turn's text/URL absent from `model_actions()`), `:1446` `test_rust_history_applies_terminal_session_compaction_boundary`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_events_after_terminal_rollbacks session.compacted replay_from_seq", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase fold (compaction re-base, then sequential rollbacks with context-attachment deletion) for any event-sourced agent log; adapt the event-type names; omit the Rust-specific `agent.mailbox_input` kinds if your transport has no mailbox concept.
