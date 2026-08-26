<!-- capsule-v2 -->
# Tolerant planner-output parse — how do you accept an LLM router's malformed JSON without re-asking the LLM?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When the API planner's structured output fails strict parsing mid-graph, what recovery ladder runs BEFORE any retry-with-the-model, and why must it never re-invoke the LLM?

## Parse-retry ladder in the router node
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/api_planner.py:_parse_planner_output_or_raise` (:40-76); strict-parse fallback call site in `ApiPlanner.node_handler` (:216-223).
**Signature:** `_parse_planner_output_or_raise(raw: str) -> APIPlannerOutput`.
**Data Shape:** raw = whatever the AIMessage content holds (plain JSON object, double-encoded JSON string, fenced JSON with prose around it). Output = validated `APIPlannerOutput` pydantic model; failure raises the LAST parse error (`raise last_err or ValueError(...)`).

### Decisive source
```python
    # Strip code fences if present
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    last_err = None
    for _ in range(3):
        try:
            obj = json.loads(s)
        except Exception as e:
            last_err = e
            # Try to slice the outermost {...}
            first, last = s.find("{"), s.rfind("}")
            if first != -1 and last > first:
                s = s[first : last + 1].strip()
                continue
            break
        # If first loads produced a JSON string, decode again (double-encoded case)
        if isinstance(obj, str) and obj.strip().startswith("{"):
            s = obj.strip()
            continue
        return APIPlannerOutput(**obj)
    raise last_err or ValueError("Planner output could not be parsed")
```

**Flow:** strip fences → up to 3 iterations of: json.loads → on failure slice outermost `{...}` and retry; on success if result is still a string starting `{` decode again; else validate into `APIPlannerOutput`. The graph node tries strict `APIPlannerOutput(**json.loads(res.content))` FIRST and only falls into this ladder on exception, logging `"Strict parse failed: {e}; trying tolerant parse..."`.
**Invariant:** Pure-parsing retries only — the docstring pins it: "does not re-ask the LLM". A port that adds an LLM repair round-trip inside this function changes cost/latency semantics and can loop; a port that drops the double-encoded branch silently breaks providers whose structured-output layer returns `json.dumps(json.dumps(obj))`.
**Probe:** No direct unit test at HEAD (recorded upstream gap). Deterministic check: `grep -c "double-encoded" src/cuga/backend/cuga_graph/nodes/api/api_planner.py` ≥ 1 and the three-step ladder lines 56-74 exist verbatim.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_parse_planner_output_or_raise tolerant parse planner", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fence-strip → outermost-slice → double-decode ladder as a pure function beside any structured-output router; adopt strict-parse-first ordering so the tolerant path stays exceptional. Adapt the target schema type and iteration count to your host. Omit re-asking the model inside this ladder (upstream deliberately routes model-driven recovery elsewhere, e.g. the blocked-claim override).
