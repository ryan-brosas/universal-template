<!-- capsule-v2 -->
# make_json_serializable coercion ladder — how do arbitrary action outputs become JSON-safe, and what changes semantics?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** What are the exact conversion branches of the local step-dict codec, and where does it silently change values rather than just stringify them?

## Heuristic, semantic-changing, deliberately lossy
**Path/Symbol:** `src/smolagents/utils.py:make_json_serializable` (:140-163). Distinct from `serialization.SafeSerializer` (typed remote codec, pass-1 capsule).
**Signature:** `make_json_serializable(obj: Any) -> Any` — recursive, returns plain containers/scalars only.
**Data Shape:** Consumers: `ToolCall.dict` arguments, `ActionStep.dict` model messages + action_output + observations path, `PlanningStep.dict`.

### Decisive source
```python
# :144-163 (selected)
if isinstance(obj, (str, int, float, bool)):
    if isinstance(obj, str):
        try:
            if (obj.startswith("{") and obj.endswith("}")) or (obj.startswith("[") and obj.endswith("]")):
                parsed = json.loads(obj)
                return make_json_serializable(parsed)   # string → dict/list: SEMANTIC CHANGE
        except json.JSONDecodeError:
            pass
    return obj
elif isinstance(obj, dict):
    return {str(k): make_json_serializable(v) for k, v in obj.items()}   # keys str()-ed
elif hasattr(obj, "__dict__"):
    return {"_type": obj.__class__.__name__, **{k: make_json_serializable(v) for k, v in obj.__dict__.items()}}
else:
    return str(obj)   # terminal fallback: bytes, sets, custom __str__...
```

**Flow:** Five ordered branches: None → None; scalars with a bracket-heuristic JSON re-parse for strings; list/tuple → list; dict → str-keyed dict; `__dict__`-bearing objects → `_type`-tagged attr dicts; everything else → `str()`. The re-parse is recursive, so a tool that returns the STRING `'{"a": 1}'` is stored in step history as the dict `{"a": 1}` — later prompt renderings show it as an object, not a quoted string.
**Invariant:** Output must always survive `json.dumps` after ANY tool output. But this codec trades fidelity for safety on purpose: tuple→list, non-str dict keys destroyed, unknown objects flattened to `__dict__` or their repr, JSON-looking strings promoted to containers. Porters who need round-tripping must NOT reuse this codec for transport — that's SafeSerializer's job (typed markers, pickle gate); this one exists so memory/replay never crashes.
**Probe:** Indirectly pinned by `tests/test_memory.py` (:237-273): a ChatMessage whose `raw` is a MockChatCompletion instance serializes through this function into `_type`-tagged JSON (`"MockChatCompletion"` present in `json.dumps(step_dict)`), proving the `__dict__` branch end-to-end. No dedicated unit test for the string-promotion branch — caveat recorded; behavior verified by direct read :146-152. Live: `make_json_serializable('{"x": [1,2]}')` returns a real dict; `make_json_serializable(object())` returns its repr string.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "make_json_serializable recursive json serializable _type dict", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: make_json_serializable utils.py :140-163 ranked #1 by wide margin.

## Verdict
Adopt the "never crash the recorder" posture and the `_type` tagging convention. Adapt the string-promotion heuristic to your risk tolerance (it can mask type errors from tools that over-quote output). Omit this codec from any durable export/transport path — pair it with a typed serializer or accept permanent information loss.
