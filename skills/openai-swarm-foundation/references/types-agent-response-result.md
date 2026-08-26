<!-- capsule-v2 -->
# Agent/Result/Response types — Why is the whole agent just six fields on a pydantic BaseModel?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What is the complete data model a porter must reproduce for agents, run responses, and function results?

## The entire ontology in 28 lines
**Path/Symbol:** `swarm/types.py:Agent` (14-20), `swarm/types.py:Response` (23-26), `swarm/types.py:Result` (29-41).
**Signature:** `AgentFunction = Callable[[], Union[str, "Agent", dict]]` (module alias; the arity is NOT enforced at runtime).
**Data Shape:** see decisive source — every field defaulted.

### Decisive source
```python
class Agent(BaseModel):
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True


class Response(BaseModel):
    messages: List = []
    agent: Optional[Agent] = None
    context_variables: dict = {}


class Result(BaseModel):
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}
```

**Flow:** `Agent` is pure data + closures (functions/instructions); `run()` reads it per turn and never mutates it; handoffs pass `Agent` INSTANCES by reference. `Response.agent` is the last active agent; `Result` is only the tool→engine channel.
**Invariant:** Agents are stateless and reentrant — all run state lives in `(history, context_variables, active_agent)`, which is why the same Agent instance can sit in multiple places of an agent graph (triage example appends the same `transfer_back_to_triage` target to two agents). `tool_choice` and `parallel_tool_calls` are forwarded verbatim to the API (`parallel_tool_calls` only when tools exist). Mutable-default lists/dicts on pydantic models are safe here (per-instance copies) but would not be on plain classes.
**Probe:** `tests/test_core.py:test_handoff` pins instance-identity semantics (`response.agent == agent2`, same object); types are otherwise covered transitively by every core test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "types Agent Response Result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt this field set as the minimal viable agent schema — every heavier framework (OpenAI Agents SDK, smolagents, agency-swarm) grew from it by adding fields, not renaming these. Adapt `instructions` typing if you need templates with variables (Swarm passes the whole context dict instead). Omit persistence/serialization: Agents here are code objects, deliberately not serializable.
