<!-- capsule-v2 -->
# triage pattern — How does the repo structure a router agent with transfer functions and a return path?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What is the canonical wiring for triage→specialist handoffs (including back-transfers) that every later framework copied?

## Zero-code routers: instructions choose, functions transfer
**Path/Symbol:** `examples/triage_agent/agents.py` (1-60).
**Signature:** `transfer_to_sales() -> Agent`, `transfer_to_refunds() -> Agent`, `transfer_back_to_triage() -> Agent`.
**Data Shape:** plain module-level Agent instances closed over by one-line functions.

### Decisive source
```python
triage_agent = Agent(
    name="Triage Agent",
    instructions="Determine which agent is best suited to handle the user's request, and transfer the conversation to that agent.",
)
...
def transfer_back_to_triage():
    """Call this function if a user is asking about a topic that is not handled by the current agent."""
    return triage_agent

def transfer_to_sales():
    return sales_agent

def transfer_to_refunds():
    return refunds_agent

triage_agent.functions = [transfer_to_sales, transfer_to_refunds]
sales_agent.functions.append(transfer_back_to_triage)
refunds_agent.functions.append(transfer_back_to_triage)
```

**Flow:** model reads each agent's `instructions` + tool docstrings → calls a `transfer_*` function → engine swaps `active_agent` → next completion uses the specialist's instructions/tools → specialists expose `transfer_back_to_triage` so control can return.
**Invariant:** The router has NO tools besides transfers; specialists keep domain tools AND a back-transfer. Transfer functions take NO parameters — identity routing only; parameterized data must flow through tool args or context_variables. Docstrings ARE the model's routing manual ("Transfer spanish speaking users immediately." in basic/agent_handoff.py). Closures over module-level instances mean agents are wired AFTER all definitions (forward references).
**Probe:** `examples/triage_agent/evals.py:test_triage_agent_calls_correct_function` (asserts the triage model selects the correct transfer function) — eval-style, LLM-dependent, not a unit test; porters should treat it as a harness example.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "Agent instructions functions list", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: router = instructions-only agent whose sole functions are zero-arg transfers to singleton agents; specialists carry domain tools plus an explicit back-transfer. Adapt with guard conditions inside transfer functions if you need policy. Omit nothing else — this ~40-line wiring is the ancestor of every supervisor/router pattern in the pack.
