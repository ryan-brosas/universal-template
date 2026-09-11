<!-- capsule-v2 -->
# DeltaChannel replay persistence — How do you checkpoint high-churn state without shipping the full value every step?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** What must a reducer guarantee so sparse checkpoints can be replayed from ancestor writes?

## Sentinel-in-blob storage + batching-invariant fold + dual-counter snapshot cadence
**Path/Symbol:** `libs/langgraph/langgraph/channels/delta.py:DeltaChannel` (:46-202), snapshot predicate `libs/langgraph/langgraph/pregel/_checkpoint.py:delta_channels_to_snapshot` (:53-69), hydration `channels_from_checkpoint` (:223-271), counter bump `_loop._put_checkpoint` (:1096-1130).
**Signature:** `DeltaChannel(reducer: (state, list[writes]) -> new_state, typ=None, *, snapshot_frequency: int = 1000)`; history via `saver.get_delta_channel_history(config, channels)`.
**Data Shape:** Checkpoint blob stores either a full `_DeltaSnapshot(value)` or NOTHING for the channel; reconstruction = find nearest seed (snapshot OR pre-migration plain value), then `replay_writes(history["writes"])`.

### Decisive source
```python
# Reducers must be deterministic and batching-invariant (associative across
# folds): applying two consecutive write batches separately must produce the
# same state as applying their concatenation once:
#     reducer(reducer(state, xs), ys) == reducer(state, xs + ys)
# Snapshot cadence is driven by two counters: per-channel update count and
# total supersteps since last snapshot. create_checkpoint writes a full
# _DeltaSnapshot blob when EITHER the update count reaches snapshot_frequency
# OR the supersteps count reaches DELTA_MAX_SUPERSTEPS_SINCE_SNAPSHOT (default 5000),
# bounding replay depth even for channels that stop receiving writes.
```
**Flow:** Every superstep bumps `(updates, supersteps)` per delta channel in metadata (`counters_since_delta_snapshot`, stored only non-zero); on snapshot both reset to (0,0). Reads hydrate by ancestor walk batched into ONE saver call for all delta channels. Overwrites are tracked in `_delta_channels_with_overwrite` and force a snapshot after live-apply so sparse replay starts from the same post-overwrite value. Message-bearing writes get ids assigned EAGERLY in put_writes (`ensure_message_ids(v)`) before background serialization — otherwise reducers assigning ids inside apply_writes race serialization and get_state() replays mint a different UUID every call.

**Invariant:** The fold-associativity law is the contract — non-associative reducers (e.g. anything order-or-chunking-sensitive like "keep last 5") silently corrupt replay. Beta status is explicit: `_DeltaSnapshot` blob shape and the history API are unstable, but threads written today stay readable.

**Probe:** `grep -c 'snapshot_frequency' libs/langgraph/langgraph/channels/delta.py` → 10; `grep -n 'DELTA_MAX_SUPERSTEPS_SINCE_SNAPSHOT' libs/langgraph/_internal/_config.py` → :33-34 (env override, default "5000"); `grep -n 'batching-invariant' libs/langgraph/graph/message.py` → :255. Direct tests: `tests/test_channels.py:345 test_delta_channel_snapshot_version_based`, `tests/test_delta_channel_supersteps_bound.py`, `tests/test_delta_channel_id_stability.py:59`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "DeltaChannel", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sentinel-checkpoint + bounded-replay design for append-dominated state (message logs, event lists). Adapt cadence numbers and env plumbing to your ops profile. Omit entirely if your state values are small — plain LastValue/BinOp checkpoints are simpler.
