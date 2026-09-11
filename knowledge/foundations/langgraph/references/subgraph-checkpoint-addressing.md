<!-- capsule-v2 -->
# Subgraph checkpoint addressing — How does a subgraph resume from its own checkpoint, not the thread head?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** Parent and subgraph share one thread but have independent checkpoint chains — how does a nested graph find the exact checkpoint it left at, and how can a user time-travel to a subgraph's own checkpoint?

## An ns→checkpoint-id map threaded through config, persisted as `parents` metadata
**Path/Symbol:** map build: `libs/langgraph/langgraph/pregel/_algo.py` — PULL node :741-744, functional call :917-920, Send push :1087-1090, error handler :1228-1231 (all four task-prep paths). Map consume: `libs/langgraph/langgraph/pregel/_loop.py` :346-360 (loop init) and :874-900 (time-travel RESUME drop); persist: `_loop.py:1126`. Restore: `libs/langgraph/langgraph/_internal/_config.py:patch_checkpoint_map` (:63-80), applied in `libs/langgraph/langgraph/pregel/main.py:_prepare_state_snapshot` (:1260).
**Signature:** `CONFIG_KEY_CHECKPOINT_MAP: dict[str, str]` mapping checkpoint_ns → checkpoint_id; `recast_checkpoint_ns(ns: str) -> str` strips numeric disambiguation segments and NS_END task-id suffixes (`_config.py:38-49`).
**Data Shape:** Every child task config gets `{**parent_map, parent_ns: checkpoint["id"]}` plus `CONFIG_KEY_CHECKPOINT_ID: None` and `CONFIG_KEY_CHECKPOINT_NS: f"{checkpoint_ns}:{task_id}"`. The map therefore holds ANCESTOR entries only during normal execution; the graph's own ns entry appears only when a snapshot is fetched with `subgraphs=True`.

### Decisive source
```python
# _loop.py init: nested graph whose OWN ns is in the map resumes from that id
        if (
            CONFIG_KEY_CHECKPOINT_MAP in self.config[CONF]
            and self.config[CONF].get(CONFIG_KEY_CHECKPOINT_NS)
            in self.config[CONF][CONFIG_KEY_CHECKPOINT_MAP]
        ):
            self.checkpoint_config = patch_configurable(
                self.config,
                {
                    CONFIG_KEY_CHECKPOINT_ID: self.config[CONF][
                        CONFIG_KEY_CHECKPOINT_MAP
                    ][self.config[CONF][CONFIG_KEY_CHECKPOINT_NS]]
                },
            )
        else:
            self.checkpoint_config = self.config
```

**Flow:** Each superstep, every prepared child task carries the parent's current checkpoint id under the parent's ns. When the subgraph's loop initializes, if its own ns is present in the map it pins `checkpoint_config` to that id — so on resume it loads exactly the checkpoint the parent recorded for it, while a fresh subgraph (ns not in map) starts from the thread head / empty state. The map is written into checkpoint metadata as `parents` on every put (`_loop.py:1126`), and `get_state` restores it onto the returned snapshot config via `patch_checkpoint_map` (`main.py:1260`). With `subgraphs=True`, `_prepare_state_snapshot` additionally fetches each pending subgraph task's own snapshot under `task_ns = f"{name}{NS_END}{task.id}"` (`main.py:1196-1227`) — this is the ONLY path that puts the subgraph's own ns into the map. Resuming from that snapshot config makes "own ns in map" true, which `_loop.py:878-900` uses as the time-travel signal: cached RESUME writes are dropped so `interrupt()` re-fires instead of returning stale values (a plain resume keeps them — multi-interrupt scenarios need previously resolved values).
**Invariant:** Ancestor entries only ⇒ normal resume; own-named entry ⇒ deliberate replay of that subgraph checkpoint, with RESUME writes invalidated. The two cases share one data structure and one boolean test, so a resumed run can never silently pick up another subgraph's checkpoint.
**Probe:** `python -m pytest "tests/test_time_travel.py::test_subgraph_replay_from_subgraph_checkpoint" -q -k memory` — passes: run to interrupt inside a subgraph, `get_state(config, subgraphs=True)`, invoke(None, sub_config) re-fires the interrupt from the subgraph's own checkpoint, then Command(resume=...) completes the whole graph. Byte-exact: `grep -c 'metadata\["parents"\] = self.config\[CONF\].get(CONFIG_KEY_CHECKPOINT_MAP, {})' libs/langgraph/langgraph/pregel/_loop.py` → 1; `grep -c 'parent_ns: checkpoint\["id"\]' libs/langgraph/langgraph/pregel/_algo.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "CONFIG_KEY_CHECKPOINT_MAP checkpoint_ns subgraph", limit: 8 });
```

## Verdict
Adopt the ancestor-map-in-config pattern for any multi-level durable runtime sharing one storage namespace: each level records (its ns → its last checkpoint id) for children, children pin to their own entry when present, and the map is persisted into checkpoint metadata so snapshots are self-describing. Keep the "own entry ⇒ replay ⇒ drop resume writes" rule explicit — conflating resume and time-travel is the classic corruption bug here. Adapt ns grammar (NS_SEP/NS_END, numeric disambiguation segments) to your host but preserve the recast step that maps runtime namespaces back to stable names.
