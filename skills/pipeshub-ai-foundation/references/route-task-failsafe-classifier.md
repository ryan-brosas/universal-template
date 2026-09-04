<!-- capsule-v2 -->
# route_task (solo-vs-multi_agent classifier with fail-safe default)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does an agent decide mid-loop whether a goal deserves multi-agent fan-out — without a broken classifier ever adding cost?

## Path/Symbol
`tools/builtin/coordination/route_task.py` — `_SYSTEM` prompt (:23–32), `_SCHEMA` (:34–41), `classify_task(model, goal, model_name=None)` standalone fn (:44–62), `RouteTaskTool` wrapper (:65–120).

## Signature
One cheap structured call: `model.complete_structured(messages=[UserMessage(goal.description)], system=_SYSTEM, output_schema=_SCHEMA)` → `{"route": "solo"|"multi_agent", "reason": str}`. `classify_task` is deliberately a PLAIN function (no Tool machinery) so any agent or preamble can invoke it.

## Data Shape
System prompt encodes the decision boundary: solo = sequential web searches (most tasks); multi_agent = 3+ INDEPENDENT workstreams each needing 5+ dedicated searches; explicit examples for both classes; "Default to solo."

### Decisive source
```python
    except Exception as exc:
        return {"route": "solo", "reason": f"classification failed, defaulted to solo: {exc}"}
```

**Flow:** ambiguous goal → route_task tool (or preamble) → structured verdict → solo: proceed directly; multi_agent: fan out via spawn_agent with depends_on wiring. The threshold vocabulary matches spawn_agent's own description ("3 or more truly independent sub-tasks", "5+ searches") so the two tools' guidance can't disagree.

**Invariant:** EVERY failure mode (exception, missing keys) degrades to solo — a broken/unavailable model must never accidentally add multi-agent cost. Classification is probabilistic and agent-invoked ("everything via tool calls"), never a deterministic preamble imposed on the agent; the root preamble may pre-inject it but any agent can re-ask mid-loop.

**Probe:** No direct unit test (coverage caveat): classify_task is exercised via preamble/orchestrator paths in tests/unit/agents/adapter/test_router.py family; the fail-safe branch is one line pinned only by source inspection here.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["classify_task","RouteTaskTool","complete_structured"]'
```

## Verdict
Adopt fail-safe-to-cheaper-route degradation and shared threshold vocabulary across router + spawner descriptions; adapt schema/prompt wording.
