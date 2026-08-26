<!-- capsule-v2 -->
# Graph activation groups — how do you run a DAG (with joins and loops) over a broadcast bus?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How does GraphFlow count down dependencies, handle all-vs-any joins, and re-arm cycles after a node fires?

## Per-(target, group) countdown + triggered-group reset
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_graph/_digraph_group_chat.py` (`GraphFlowManager.__init__` :312–364, `update_message_thread` :392–425, `_reset_triggered_activation_groups` :438–456, `select_speaker` :458–468, `_apply_termination_condition` :473–504).
**Signature:** `async def update_message_thread(self, messages: Sequence[...]) -> None` (override); `async def select_speaker(self, thread) -> List[str]`.
**Data Shape:** Mutable execution state: `_remaining: Dict[target, Counter[group]]` (edges still owed per join group), `_enqueued_any: Dict[target, Dict[group, bool]]`, `_ready: Deque[str]`, `_triggered_activation_groups: Dict[node, Set[group]]`. Edge fields: `condition` (string-in-message or callable), `activation_group` (defaults to target name), `activation_condition: "all"|"any"`.

### Decisive source
```python
for edge in self._edges[source]:
    if not edge.check_condition(message):
        continue
    target, activation_group = edge.target, edge.activation_group
    if self._activation[target][activation_group] == "all":
        self._remaining[target][activation_group] -= 1
        if self._remaining[target][activation_group] == 0:
            self._ready.append(target)                     # join satisfied
            self._save_triggered_activation_group(target, activation_group)
    else:
        # any: enqueue once per group no matter how many parents fired
        if not self._enqueued_any[target][activation_group]:
            self._ready.append(target)
            self._enqueued_any[target][activation_group] = True
```
```python
# select_speaker drains the queue AND re-arms the groups that fired:
for activation_group in self._triggered_activation_groups[speaker]:
    if self._activation[speaker][activation_group] == "any":
        self._enqueued_any[speaker][activation_group] = False
    else:
        self._remaining[speaker][activation_group] = self._origin_remaining[speaker][activation_group]
```

**Flow:** agent publishes → manager's thread-update walks the speaker's OUTGOING edges → condition-gated decrements/enqueues → next turn drains ALL ready nodes at once (parallel fan-out) → chat ends when `_ready` stays empty ("Digraph execution is complete") with full state re-init for reruns.
**Invariant:** countdown state is keyed by `(target, activation_group)`, NOT by parent — two cycles converging on one node stay independent; re-arm happens when the node is DEQUEUED (fired), so loops like A→B→C→B work by restoring B's remaining-count only after B actually runs; construction-time validation rejects mixed conditional/unconditional outgoing edges, conflicting activation conditions within a target+group, and ANY cycle lacking a conditional exit edge (`has_cycles_with_exit` raises ValueError), and cyclic graphs require a termination condition or max_turns (:340–341).
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat_graph.py::test_digraph_group_chat_parallel_join_all` / `::test_digraph_group_chat_parallel_join_any` / `::test_cycle_detection_without_exit_condition` / `::test_digraph_group_chat_loop_with_two_cycles`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "GraphFlowManager _remaining _enqueued_any activation_group select_speaker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt (target, group)-keyed join counting with fire-time re-arm — it is the minimal correct semantics for fan-in joins AND loops on top of any message bus. Adapt edge conditions to structured predicates rather than string-in-text. Omit callable-condition serialization caveats (they're excluded from dumps by design).
