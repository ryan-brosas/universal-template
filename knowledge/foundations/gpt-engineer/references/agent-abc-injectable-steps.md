<!-- capsule-v2 -->
# agent-abc-injectable-steps — What is the minimal agent interface, and how do CLI modes swap steps without subclasses?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** Which two methods define an agent, and how does CliAgent parameterize behavior via function injection?

## Agent abstraction seam
**Path/Symbol:** `gpt_engineer/core/base_agent.py:BaseAgent` (:17-31); `gpt_engineer/applications/cli/cli_agent.py:CliAgent.__init__` (:84-100) + `init` (:152-183); `gpt_engineer/core/default/simple_agent.py:SimpleAgent` (:27-100).
**Signature:** `BaseAgent.init(prompt) -> FilesDict`; `BaseAgent.improve(files_dict, prompt) -> FilesDict` (both abstract).
**Data Shape:** CliAgent holds THREE injected callables: `code_gen_fn(ai,prompt,memory,preprompts_holder)->FilesDict`, `improve_fn(ai,prompt,files_dict,memory,preprompts_holder,diff_timeout)->FilesDict`, `process_code_fn(ai,execution_env,files_dict,**kw)->FilesDict`.

### Decisive source
```python
# main.py mode wiring — composition over subclassing
if clarify_mode:      code_gen_fn = clarified_gen
elif lite_mode:       code_gen_fn = lite_gen
else:                 code_gen_fn = gen_code
if self_heal_mode:    execution_fn = self_heal
else:                 execution_fn = execute_entrypoint
...
agent = CliAgent.with_default_config(memory, execution_env, ai=ai,
    code_gen_fn=code_gen_fn, improve_fn=improve_fn,
    process_code_fn=execution_fn, preprompts_holder=preprompts_holder)
```

**Flow:** CLI flags → pick gen fn (clarified|lite|default) → pick process fn (self_heal|execute_entrypoint) → inject into ONE concrete CliAgent → `init()` runs code_gen_fn then ALWAYS gen_entrypoint then process_code_fn with kwargs `(preprompts_holder=, prompt=, memory=)` merged.
**Invariant:** (1) The whole mode matrix is function injection — NO subclass per mode; adding a mode = writing one step function + one flag. (2) init() hard-wires `gen_entrypoint` between generation and processing — custom code_gen fns must produce files whose entrypoint can be generated; improve() deliberately does NOT re-run entrypoint (commented-out block :218-230 documents that decision). (3) SimpleAgent vs CliAgent differ ONLY in defaults: SimpleAgent fixes gen_code/improve_fn and takes execution_command param it ignores; CliAgent accepts the step bundle. BaseAgent ABC keeps both honest. (4) process_code_fn receives extra kwargs via **merge — execute_entrypoint and self_heal share the signature `(ai, execution_env, files_dict, prompt=None, preprompts_holder=None, memory=None)`; a ported replacement must accept-and-ignore these.
**Probe:** `grep -c 'code_gen_fn' gpt_engineer/applications/cli/main.py` → 5 (:484/:486/:488 assignments, :508 injection, :545 telemetry config tuple).
**Probe:** `grep -c '= gen_entrypoint(' gpt_engineer/applications/cli/cli_agent.py` → 2 (:170 live call in init, :218 commented-out improve variant — the pair documents the deliberate asymmetry).
**Probe:** `grep -n '@abstractmethod' gpt_engineer/core/base_agent.py` → 2 (init, improve).
**Probe:** `tests/core/default/test_simple_agent.py::test_init/test_improve` run the real SimpleAgent against MockAI — interface spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "CliAgent code_gen_fn process_code_fn BaseAgent", limit: 10 });
```

## Verdict
Adopt two-method agent ABC + injected step functions as the minimal-agent skeleton; adapt the step signatures to your IO types; omit the ignored execution_command param. This is the repo's core architectural lesson: modes are data (functions), not class hierarchies.
