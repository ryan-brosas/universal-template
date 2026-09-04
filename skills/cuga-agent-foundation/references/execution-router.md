<!-- capsule-v2 -->
# ExecutionRouter — three-axis execution backend resolution with behavior-preserving legacy fallback

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A code-executing agent needs an explicit, prompt-visible description of WHERE code runs (local python vs remote sandbox; shell; filesystem), while remaining behavior-identical to a legacy single-flag (`e2b_sandbox`) decision. How do you model three independent backends and resolve them without breaking existing behavior?

## The router
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/policy/execution_policy.py` (`ExecutionPlan` :25-42, `split_execution_note` :45-59, `ExecutionRouter.resolve` :62-141).
**Signature:** `ExecutionRouter.resolve(settings, *, mode=None, workspace_root=None) -> ExecutionPlan`.
**Data Shape:** `ExecutionPlan` carries `requested_backend`, `python_backend: "local"|"e2b"`, `shell_backend: "none"|"local"|"native"|"opensandbox"|"e2b"`, `filesystem_backend: "none"|"host"|"sandbox_remote"`, `local_control_tools=["find_tools","load_skill"]`, `fallbacks: List[str]`, `workspace_root="/workspace"`, `variable_transfer_policy="namespace"`.

### Decisive source
```python
# execution_policy.py:84-96 — python_backend reproduces EXACTLY the legacy decision
e2b = bool(getattr(adv, "e2b_sandbox", False))
settings_choice = explicit_python if explicit_python is not None else ("e2b" if e2b else "local")
if mode is not None:
    python_backend = mode
    if mode != settings_choice:
        fallbacks.append(f"python_backend forced to '{mode}' by explicit mode (settings would select '{settings_choice}')")
else:
    python_backend = settings_choice

# execution_policy.py:37-42 — split execution: python local while shell/FS run remotely
def split_execution_active(self):
    remote_shell = self.shell_backend in ("native", "opensandbox", "e2b")
    remote_fs = self.filesystem_backend == "sandbox_remote"
    return self.python_backend == "local" and (remote_shell or remote_fs)
```

**Flow:** explicit `execution.*` settings take priority over legacy `advanced_features` flags (None means "not set" → fall through). `python_backend`: explicit > `mode` override (records a fallback note when it differs) > legacy `e2b_sandbox`. `shell_backend`: explicit > legacy `enable_shell_tool` (mapping `sandbox_mode` to a valid value, else "none"). `filesystem_backend`: explicit > `enable_filesystem_tools` → `"sandbox_remote"` iff shell is `opensandbox` else `"host"`, else "none". Deprecation warnings are appended to `fallbacks` when explicit settings disagree with legacy flags. `split_execution_note` returns a prompt-visible warning when python runs locally but shell/FS run remotely.
**Invariant:** The resolution is behavior-preserving — `python_backend` reproduces exactly the implicit decision in `CodeExecutor.eval_with_tools_async` ("e2b" iff `advanced_features.e2b_sandbox`, else "local"). The shell/filesystem axes merely describe existing flag behavior; no graph consumes the plan yet. Explicit `execution.*` wins over legacy flags, and a deprecation note is recorded rather than silently ignored.
**Probe:** `tests/graph/test_supervisor_feature_parity.py` item 4 pins `split_execution_note` non-empty exactly when the plan is split-active (so both graphs' `filter(None, [...])` joins include it correctly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ExecutionRouter ExecutionPlan split_execution_active python_backend e2b_sandbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-axis backend model (python/shell/filesystem), the explicit-wins-over-legacy resolution with recorded fallback notes, and the behavior-preserving contract. Adapt the backend literals to your sandbox providers. Omit the `split_execution_note` wording and `local_control_tools` list unless your prompt needs them.
