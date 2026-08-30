<!-- capsule-v2 -->
# Function-tool lookup keys & collision resolution — how are bare/namespaced/deferred tool names routed without ambiguity?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** What identity does a function tool expose on the wire, and what happens when two tools claim one name?

## Three-kind lookup keys + winner-takes-all collision ladder
**Path/Symbol:** `src/agents/_tool_identity.py:` `FunctionToolLookupKey` union (:13–20), `get_function_tool_lookup_key*` (:176–205), `resolve_tool_name_collisions` (:503–552), `validate_function_tool_lookup_configuration` (:555–594), `get_function_tool_approval_keys` (:607–655).
**Signature:** `def resolve_tool_name_collisions(tools, handoffs=(), *, collision_policy: Literal["warn", "error"]) -> tuple[list[Any], list[Any]]`.
**Data Shape:** keys: `("bare", name)` | `("namespaced", namespace, name)` | `("deferred_top_level", name)` — the last is SYNTHETIC: reserved when `namespace == name` on a call payload, produced by deferred-loading tools without an explicit namespace.

### Decisive source
```python
winner = handoff_entries[-1] if handoff_entries else entries[-1]
for entry_type, index, _ in entries:
    if (entry_type, index) == (winner[0], winner[1]):
        continue
    ...  # discard every loser from the retained lists
```
Validation first: duplicate qualified names raise UNLESS both sides are namespace-free (bare dotted-name duplicates stay legal); two deferred top-level tools sharing a name always raise; an explicit namespace equal to its own tool name raises (reserved wire shape). Error messages are diagnostic-grade: they detect which agents DERIVED colliding names (vs overrode them) and name the exact override parameter (`tool_name=` vs `tool_name_override=`).

**Flow:** validate configuration → group bare-key owners (tools + handoff tool-names) → on collision: `error` policy raises with the tailored message; `warn` policy logs (or redacts under DONT_LOG_TOOL_DATA) then keeps only the LAST handoff owner or overall-last entry, discarding other claimants → return filtered lists used for model exposure AND span metadata. Approval keys derive per lookup kind (`bare:` name, namespaced `ns.name`, `deferred_top_level:name`) with optional legacy aliases.

**Invariant:** Collision resolution happens BEFORE model exposure (never mid-dispatch) and is deterministic (last-wins, handoffs preferred); namespaces exist precisely so same-name tools coexist — but the synthetic deferred shape must stay unambiguous.

**Probe:** `tests/test_tool_name_collision_policy.py` (:51 warn-rebind, :79 error-before-side-effects, :110 cross-kind reclassification rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "resolve tool name collisions lookup key deferred top level", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed lookup keys + pre-exposure collision arbitration for any plugin/namespace tool registry; adapt key kinds to your routing needs; the derived-vs-overridden diagnostics pattern is worth porting verbatim.
