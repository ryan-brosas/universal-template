<!-- capsule-v2 -->
# Approval ledger — scope AND precision with the human's words attached

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How are human approvals serialized so a "no" applies exactly to the right call and the reason survives resume?

## The approval ledger
**Path/Symbol:** `src/agents/run_state.py` (approval serialization :1296-1390, reject() :1266-1289, canonical invocation ledger schema 1.15).
**Signature:** per-tool approved/rejected booleans OR call-id lists; hosted MCP approvals as sorted `{identity, decision}` pairs; canonical invocation ledger `call_id → {type, approval_scope, fingerprint, executed, completed}`.
**Data Shape:** `rejection_messages` and `sticky` fields optional; identity is a discriminated union (`server_tool | request | query`).

### Decisive source
```python
# reject()'s docstring (:1266-1289):
#   "When rejection_message is provided, that exact text is sent back to the model when the run resumes."
```

**Flow:** Local tool approvals serialize per tool as approved/rejected booleans OR call-id lists, plus optional rejection_messages and sticky fields (:1296-1320). Hosted MCP approvals serialize as sorted {identity, decision} pairs (:1337-1390). A separate canonical invocation ledger maps call_id → {type, approval_scope, fingerprint, executed, completed} (schema 1.15). Approvals are security state, not UI state: a "no" must apply exactly to the offending call_id or stick to the tool deliberately, and the reason the human gave must be the reason the model sees after resume. Pre-1.15 blobs reconstruct legacy bindings from restored calls+outputs, deferring unresolvable pendings into `_restored_unbound_approval_call_ids`.
**Invariant:** Serialize approvals as BOTH scope (tool-level) and precision (call-id lists) with the human's rejection text attached — and version the ledger format because its fidelity grows over time.
**Probe:** :891-904 (rejection message stored); :1310+ (call-scoped rejection); migration probes strip rejection_messages under 1.5 and force legacy reconstruction under 1.15.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "rejection_message approval ledger call_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scope+precision approval serialization with rejection text attached and a versioned ledger; adapt the identity union shape; omit hosted-MCP specifics. Direct tests pin rejection-message persistence.
