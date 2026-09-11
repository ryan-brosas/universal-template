<!-- capsule-v2 -->
# Parking & resume — detached snapshots, identity re-binding, ambiguity fails loud

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How are pending approvals parked while paused and re-bound to the live run on resume, safely?

## Parking and resuming approvals
**Path/Symbol:** `src/agents/run_state.py` (get_interruptions :981-1051, decision re-binding :1053-1089, staging :937-979, :1626, :1702, :1921).
**Signature:** `get_interruptions()` returns detached copies of `ToolApprovalItem`; decision matcher re-binds via canonical invocation identity.
**Data Shape:** canonical invocation identity = (type, call_id, scope, fingerprint); matcher is tri-state (True/False/None).

### Decisive source
```python
# While paused, get_interruptions() hands out DETACHED copies of ToolApprovalItem (:981-1051).
# If an item can't be safely copied, it fails closed:
#   "Cannot safely copy pending tool approvals…" (:1008-1011)
# Ambiguity RAISES: "Cannot apply approval because multiple current pending approvals contain
# the same tool invocation identity… Use unique call IDs." (:1053-1089)
```

**Flow:** When a decision returns, the detached copy is matched back to the live item via canonical invocation identity — searched recursively through nested agent-as-tool run states — and any ambiguity RAISES. The matcher is tri-state (True/False/None): None means "unsafe to distinguish," which callers treat as failure. Copy hardening extends to payloads: cyclic references raise TypeError('Cyclic tool approval payload'), non-finite numbers are rejected, and Pydantic dunder hooks (`__getattr__`, `__getattribute__`) sit in an unsafe-subtype blocklist (:250-286). User input can be STAGED during the pause but only when a next model call is guaranteed — staging refuses terminal states, exhausted turns, accepted-but-unprocessed responses, and stop-at-tool interruptions verbatim: "Cannot add input to an interrupted RunState whose tool result may end the run" (:937-979).
**Invariant:** Park approvals as immutable identity-bearing snapshots, re-bind decisions by canonical identity, stage user input only when a model call is guaranteed, and make every ambiguity a loud error.
**Probe:** :1626 (detached-snapshot round-trip applies decisions); :1702 (unsafe snapshots fail before return); :1921 (identity collisions rejected); pending-input tests at `test_run_state_pending_input.py:286/:363/:957`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "get_interruptions ToolApprovalItem canonical invocation identity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt detached-immutable-snapshot parking, canonical-identity re-binding, tri-state matcher, and loud ambiguity; adapt the identity tuple shape; omit nested agent-as-tool recursion specifics. Direct tests pin the round-trip and collision behaviors.
