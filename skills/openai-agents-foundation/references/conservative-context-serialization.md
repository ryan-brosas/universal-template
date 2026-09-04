<!-- capsule-v2 -->
# Conservative context serialization — never fake a round trip you can't perform

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How is arbitrary context serialized into a resumable snapshot without silently losing type information?

## Conservative context serialization
**Path/Symbol:** `src/agents/run_state.py` (context serialization :1456-1549, restore precedence :3861-3869, :906-937, :1050-1069, :651-664).
**Signature:** context serialization by capability tier; `context_meta` travels in the blob.
**Data Shape:** `context_meta` = {original_type, serialized_via, requires_deserializer, omitted}.

### Decisive source
```python
# Contexts serialize by capability tier (:1456-1549):
#   mappings restore directly; Pydantic models dump via model_dump and dataclasses via asdict —
#   both WARNING that the original TYPE is gone; anything else serializes to {} marked omitted.
# Restore precedence (:3861-3869): context_override -> context_deserializer -> direct mapping restore,
# with warnings or raises rather than "silently claiming that the rebuilt mapping is equivalent
# to the original object." RunContextWrapper SUBCLASSES are explicitly rejected.
# class_path in metadata is diagnostic only: "never auto-import it for safety."
```

**Flow:** A machine-readable `context_meta` {original_type, serialized_via, requires_deserializer, omitted} travels in the blob so restore-time code can warn, demand a deserializer, or hard-fail under `strict_context`. Under strict mode, dropping non-mapping context raises `UserError("…Provide context_serializer to serialize custom contexts.")` rather than silently omitting.
**Invariant:** Never fake a round trip you can't perform — serialize what's safe, attach machine-readable metadata describing the gap, and force callers to acknowledge it at restore time.
**Probe:** :906-937 (non-mapping warns/omits + strict requires serializer); :1050-1069 (pydantic metadata recorded); :651-664 (duplicate identity references fail loudly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "context_meta serialized_via requires_deserializer strict_context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-tier serialization with machine-readable gap metadata and strict-mode enforcement; adapt the exact context_meta fields; omit provider-specific context types. Direct tests pin the warn/omit/strict behaviors.
