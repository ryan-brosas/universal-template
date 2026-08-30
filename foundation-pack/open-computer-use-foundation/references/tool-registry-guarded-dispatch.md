<!-- capsule-v2 -->
# Tool registry + guarded dispatcher — how do tools get declared and safely invoked without hard-wiring?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How does an agent declare callable tools so an LLM can invoke them by name, without letting arbitrary names reach methods or exceptions escape into the loop?

## Module-level registry filled by a class-scoped decorator
**Path/Symbol:** `os_computer_use/sandbox_agent.py:15-20` (`tools` dict), `:42-52` (`SandboxAgent.call_function`), `:54-59` (`SandboxAgent.tool` decorator).
**Signature:** `tools = {"stop": {"description": str, "params": {}}}`; `call_function(self, name, arguments)`; `def tool(description, params)` returning `decorator(func)`.
**Data Shape:** Registry values are `{description: str, params: {param_name: description_str}}` — param descriptions double as schema docs later. `"stop"` is pre-seeded at module import so the loop has a termination verb even before any decorated method exists. Note the decorator is defined INSIDE the class body but is NOT a `classmethod`/`staticmethod` — at class-creation time it is a plain function whose closure receives the decorated function.

### Decisive source
```python
def call_function(self, name, arguments):
    func_impl = getattr(self, name.lower()) if name.lower() in tools else None
    if func_impl:
        try:
            result = func_impl(**arguments) if arguments else func_impl()
            return result
        except Exception as e:
            return f"Error executing function: {str(e)}"
    else:
        return "Function not implemented."
```

**Flow:** LLM emits `{name, parameters}` → membership check `name.lower() in tools` gates `getattr` (an unregistered name NEVER resolves to a method, even one that exists on the class) → invocation kwargs-spreads arguments → ANY exception becomes a string result → unknown names return the literal `"Function not implemented."`.
**Invariant:** Every failure mode returns a STRING the model can read as an observation; nothing raises out of the dispatcher, and no non-tool attribute of the agent is reachable because the registry check happens BEFORE `getattr`.
**Probe:** `cd /mnt/hdd/utopia/inspo/external/open-computer-use && sed -n '42,59p' os_computer_use/sandbox_agent.py` (shows gate-before-getattr order and the bare `tools` reference); direct test harness `tests/sandbox_agent.py:28` instantiates `SandboxAgent(MockSandbox(), save_logs=False)` proving the dispatcher runs against a stub sandbox.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "call_function tool registry decorator", limit: 8, fields: ["signature", "name", "file"] });
// expect ext-open-computer-use.os_computer_use.sandbox_agent.SandboxAgent.call_function (sandbox_agent.py 42-52) and .tool (54-59)
```

## Verdict
Adopt the registry-gated dispatch pattern (`name.lower() in tools` before `getattr`, exception→string) for any LLM tool loop; adapt the global-dict scope if you need per-instance toolsets (here the registry is intentionally module-global and shared across instances); omit the implicit coupling that tool method names must equal registry keys.
