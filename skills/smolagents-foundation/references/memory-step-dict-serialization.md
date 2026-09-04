<!-- capsule-v2 -->
# Memory-step dict serialization — how do steps become JSON-safe dicts, and what is silently lossy?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** What is the exact dict shape of ActionStep/PlanningStep/ToolCall serialization, which fields get lossy treatment, and how does it differ from the wire JSON posture?

## Hand-built step dicts over the local heuristic codec
**Path/Symbol:** `src/smolagents/memory.py` — `ToolCall.dict` (:30-38), `MemoryStep.dict` (asdict, :43-44), `ActionStep.dict` (:66-90), `PlanningStep.dict` (:161-172); helpers `models.get_dict_from_nested_dataclasses` (:70-76), `utils.make_json_serializable` (:140-163).
**Signature:** `ActionStep.dict(self) -> dict` — fixed literal key set, not `asdict`.
**Data Shape:** Consumers: `RunResult.steps = memory.get_full_steps()` (`agents.py:528`); `get_succinct_steps` drops ONLY the `model_input_messages` key.

### Decisive source
```python
# memory.py :66-90 (selected lines)
return {
    "step_number": self.step_number,
    "timing": self.timing.dict(),
    "model_input_messages": [make_json_serializable(get_dict_from_nested_dataclasses(msg)) for msg in ...],
    "tool_calls": [tc.dict() for tc in self.tool_calls] if self.tool_calls else [],
    "error": self.error.dict() if self.error else None,          # {"type": classname, "message": str}
    "model_output_message": make_json_serializable(get_dict_from_nested_dataclasses(...)),
    "observations_images": [image.tobytes() for image in self.observations_images] if ... else None,
    "token_usage": asdict(self.token_usage) if self.token_usage else None,
    "is_final_answer": self.is_final_answer,
}
```

**Flow:** ToolCall.dict bakes the OpenAI function-call envelope (`{"id", "type": "function", "function": {"name", "arguments"}}`) with arguments through make_json_serializable. ChatMessage sub-dicts KEEP their `raw` field (a non-serializable object becomes `{"_type": "MockChatCompletion", ...}` via the `__dict__` branch and stays json.dumps-able) — contrast with `ChatMessage.model_dump_json`, which strips `raw` via `ignore_key="raw"`. Images serialize as bare `bytes` from `.tobytes()` with NO mode/size/dtype recorded: irreversible. MessageRole survives as a str-Enum that compares equal to its string value.
**Invariant:** Step dicts must remain json.dumps-able after arbitrary tool outputs — every escape hatch (heuristic parse, `_type` tagging, str fallback) serves that one property. But "JSON-safe ≠ information-preserving": porting this shape verbatim gives you un-reconstructable observation images; keep a parallel raw channel (like model_input_messages retention in full vs succinct steps) if you need fidelity.
**Probe:** `tests/test_memory.py::test_action_step_dict` (:52-117): exact per-key assertions — timing {"start_time","end_time","duration"}, token_usage asdict includes derived total_tokens=30, tool_calls OpenAI shape with parsed arguments dict; `tests/test_memory.py::test step serialization keeps raw usable` (:237-273): `"MockChatCompletion"` appears in `json.dumps(step_dict)` for both ActionStep and PlanningStep. Live: build an ActionStep with a PIL image observation → `.dict()["observations_images"]` is list[bytes] with no dimensions attached.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "ActionStep dict PlanningStep ToolCall token_usage observations_images serialization", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: ToolCall.dict :30-38, ActionStep.dict :66-90, PlanningStep.dict :161-172 are top-3.

## Verdict
Adopt the fixed-key dict contract and the two-tier full/succinct accessors. Adapt the codec to your serializer (typed markers instead of `_type`+`__dict__`). Omit blind `.tobytes()` image dumps from any durable export — pair bytes with metadata or store references.
