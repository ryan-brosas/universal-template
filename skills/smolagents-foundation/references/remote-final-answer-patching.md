<!-- capsule-v2 -->
# Remote final-answer patching — how does a sandboxed final_answer signal cross the process boundary?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** Remote executors can't catch Python exceptions raised inside the sandbox — so how is `final_answer` re-implemented to carry both the control signal AND its payload back over stdout/Jupyter protocols?

## Source-extracted exception wrapper
**Path/Symbol:** `src/smolagents/remote_executors.py:RemotePythonExecutor._patch_final_answer_with_exception` (:143-304), `_deserialize_final_answer` (:306-332), `FINAL_ANSWER_EXCEPTION="FinalAnswerException"` (:68).
**Signature:** Patches the tool INSTANCE's class in place: `final_answer_tool.__class__ = _FinalAnswerTool` where `forward` raises `FinalAnswerException(_serialize_with_fallback(self._forward(*args, **kwargs)))`.
**Data Shape:** Payload is `"safe:" + json.dumps(json_safe)` or, when `allow_pickle=True`, `"pickle:" + base64(pickle)`. The remote error surfaces as E2B `execution.error.name == "FinalAnswerException"` with `.value` = prefixed string, or Jupyter msg `content.ename == "FinalAnswerException"` with `evalue`.

### Decisive source
```python
# :288-291 — closures do NOT survive source extraction; constants are textually baked in:
source = inspect.getsource(forward)
source = source.replace("ALLOW_PICKLE = allow_pickle_setting", f"ALLOW_PICKLE = {allow_pickle_setting}")
forward.__source__ = source
# :295-304 — original forward preserved under a new name, then class swap:
original_forward_function = final_answer_tool.forward.__func__
_FinalAnswerTool._forward = original_forward_function
...
final_answer_tool.__class__ = _FinalAnswerTool
```

**Flow:** `send_tools` patches the final_answer tool BEFORE installing definitions; sandbox-side call → `_forward` runs the user logic once → inline serializer (a full copy of SafeSerializer.to_json_safe + fallback logic, INLINED because remote environments have no smolagents import) → raise FinalAnswerException(BaseException) with serialized string → host sees the well-known ename and calls `_deserialize_final_answer`: `safe:` prefix always accepted; `pickle:` prefix ONLY with `allow_pickle=True` else SerializationError "Pickle data rejected"; NO prefix → hard reject (legacy-format defense). The same prefix gate guards `send_variables` deserialization codegen (`SafeSerializer.get_deserializer_code(allow_pickle)` bakes the pickle branch in or out at generation time).
**Invariant:** Three-way contract: (1) the raising class must derive BaseException remotely too (sandbox code's try/except must not eat it); (2) every constant the extracted source references must be baked into its text — closures die at extraction; (3) unprefixed payloads are rejected even in allow_pickle mode's safe path... rather: unprefixed payloads are ALWAYS rejected because legacy no-prefix pickle data is indistinguishable from an attack. Forgetting (2) ships a NameError only when the feature flag flips.
**Probe:** `tests/test_remote_executors.py::TestRemotePythonExecutor.test_deserialize_final_answer_rejects_unprefixed_payload` (:75), `test_send_variables_with_empty_dict_is_noop` (:36), `test_send_variables_allow_pickle_handles_prefixed_payload` (:61); integration twins per backend (:190+). Live: `_deserialize_final_answer("no-prefix", False)` → SerializationError "Unknown final answer format".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "_patch_final_answer_with_exception FinalAnswerException deserialize", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt instance-class-swap patching with textual constant baking whenever generated/host code must be shipped into a foreign runtime. Adapt the transport mapping (E2B result objects vs Jupyter wire messages vs Modal tunnels). Omit the inlined serializer copy only if your sandbox can import the host package — smolagents inlines it precisely because it usually cannot.
