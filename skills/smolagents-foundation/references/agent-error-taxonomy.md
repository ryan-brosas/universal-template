<!-- capsule-v2 -->
# Agent error taxonomy — which error classes exist, what does constructing one do, and what is the dict contract?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `smolagents`. **Question:** What is the exact AgentError class hierarchy, why does raising one already log, and what shape does `.dict()` hand to step serialization?

## Six-class tree with log-on-construct
**Path/Symbol:** `src/smolagents/utils.py` — `AgentError` (:92-101), `AgentParsingError` (:104-107), `AgentExecutionError` (:110-113), `AgentMaxStepsError` (:116-119), `AgentToolCallError` (:122-125), `AgentToolExecutionError` (:128-131), `AgentGenerationError` (:134-137).
**Signature:** `AgentError(message, logger: AgentLogger)`; `dict(self) -> dict[str, str]`.
**Data Shape:** `.dict()` = `{"type": self.__class__.__name__, "message": str(self.message)}`.

### Decisive source
```python
# :95-101 — construction has a side effect:
def __init__(self, message, logger: "AgentLogger"):
    super().__init__(message)
    self.message = message
    logger.log_error(message)          # raising == logging, everywhere

def dict(self) -> dict[str, str]:
    return {"type": self.__class__.__name__, "message": str(self.message)}
```

**Flow:** Tree: base → Parsing / Execution / MaxSteps / Generation; ToolCall and ToolExecution nest under Execution. This shape powers two load-bearing behaviors documented in sibling capsules: runloop-exit-machine's asymmetry (AgentError = model's fault → stored as `action_step.error`; AgentGenerationError = harness fault → crash) and memory-step-rendering's retry-coaching text wrapped around `str(self.error)` when projected into the next prompt. The classname travels verbatim inside step dicts (`"type": "AgentMaxStepsError"`), so downstream triage can branch on it without importing classes.
**Invariant:** Every raise site must pass a logger because the constructor logs — instantiating an AgentError without one is a TypeError, keeping "raised" and "reported" inseparable. The type/message pair must stay lossless: it is the ONLY error record that survives into RunResult.steps and replay.
**Probe:** Indirect but pinned: `tests/test_agents.py::test_fails_max_steps` (:501-521) asserts the final memory step carries an `AgentMaxStepsError` (classname equality via isinstance + type string through step dicts); `tests/test_memory.py::test_action_step_dict` pins `"error": None` key presence. No dedicated unit test asserts `.dict()`'s exact shape — caveat recorded; verified by direct source read at :100-101 and by its single consumer ActionStep.dict :77. Live: `AgentParsingError("bad", logger).dict()` → `{"type": "AgentParsingError", "message": "bad"}` plus one console error line emitted before `.dict()` runs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "AgentError AgentParsingError AgentToolExecutionError AgentGenerationError dict message logger", limit: 8, fields: ["signature", "lines"] });
```
Executed at pin: AgentError.dict :100-101 (#1), agent_logger fixture tests/test_agents.py :109-112, AgentError.__init__ :95-98 top-3.

## Verdict
Adopt the six-class tree plus log-on-construct coupling and the {type: classname, message} dict contract for anything that crosses a serialization boundary. Adapt class names to your domain vocabulary but keep them stable strings — they are wire data. Omit a separate "internal vs model" flag only if you keep the GenerationError escape hatch that crashes instead of coaching.
