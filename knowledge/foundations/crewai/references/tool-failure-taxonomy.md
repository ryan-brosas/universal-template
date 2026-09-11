<!-- capsule-v2 -->
# Tool failure taxonomy — how does a tool say "I ran but failed", and what do ignore/warn/raise mean at each call site?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How does the framework distinguish declared failures from error-looking strings, and how is the policy resolved and applied?

## ToolFailure / ToolFailurePolicy / handle_tool_failure
**Path/Symbol:** `lib/crewai/src/crewai/tools/tool_failure.py:35-45` (`ToolFailureReason`), `:57-68` (`ToolFailurePolicy`), `:71-124` (`ToolFailure`), `:126-176` (`ToolFailureRecord`), `:186-224` (`resolve_tool_failure_policy`), `:324-384` (`handle_tool_failure`).
**Signature:** `def resolve_tool_failure_policy(tool=None, agent=None, task=None, crew=None) -> ToolFailurePolicy`; `def handle_tool_failure(failure, *, tool_name, tool_args=None, tool=None, agent=None, task=None, crew=None) -> ToolFailureRecord | None`.
**Data Shape:** `ToolFailure(message, reason, code=None, retryable=False, details={})` frozen Pydantic; reasons = `tool_reported | exception | mcp_error | usage_limit | unknown_tool | invalid_input`. `ToolFailureRecord` adds tool_name/args/agent_role/task_name/task_id and lands on `TaskOutput.tool_failures`.

### Decisive source
```python
class ToolFailurePolicy(str, Enum):
    IGNORE = "ignore"  # "Pre-1.16 behavior: not recorded, emitted, or acted on"
    WARN   = "warn"    # record + event + keep going. The default.
    RAISE  = "raise"   # record + event + abort with ToolExecutionFailedError

def detect_tool_failure(result):        # "strictly declarative -- nothing
    if isinstance(result, ToolFailure): #  here guesses whether a string
        return result                   #  'looks like' an error."
    return None

for source in (tool, original_tool, task, agent, crew):   # most specific wins
    policy = getattr(source, "tool_failure_policy", None)
    ...
# malformed policy value → logger.warning + continue (never breaks the call)
```

**Flow:** Detection happens on every execution path (ReAct via `execute_tool_and_check_finality`, native batch, StepExecutor) right after the raw result exists — including on CACHE hits (`detect_tool_failure(cached_result)`). Reporting: `_record_failure` appends to a ContextVar-scoped collector AND the agent's best-effort list, then emits `ToolFailureDetectedEvent` carrying the policy; RAISE then throws `ToolExecutionFailedError(record)`. Callers deliberately re-raise that exception OUT of generic except-blocks (executor `execute_tool_action`, parallel fan-out, StepExecutor) because folding it into an observation would let the run continue after an explicit abort. `reportable_failure` returns None under IGNORE so even the finished-event flag disappears from trace UIs. Collector isolation: `tool_failure_collector()` ContextVar so concurrent tasks sharing one agent never see each other's records.
**Invariant:** CacheHandler.add REFUSES to store ToolFailure outputs ("replaying one would make a transient error permanent for the rest of the run"); hook-blocked results RESET a previously-detected cached failure (`tool_failure = None`) so the block isn't misattributed. Policy resolution must read BOTH the CrewStructuredTool wrapper and its `_original_tool`, "otherwise a tool-scoped policy is ignored on every native function-calling path".
**Probe:** `tests/tools/test_tool_failure.py::TestMalformedArgsOnEveryPath.test_react_path_reports_a_malformed_call` (and sibling per-path tests); cache refusal pinned in `tests/agents/test_agent_executor.py` cache tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "handle_tool_failure ToolFailurePolicy", limit: 6, detail: "ids" });
// → handle_tool_failure Function …/tools/tool_failure.py 324-384; ToolFailurePolicy Class 57-68
```

## Verdict
Adopt the typed-failure + three-policy model with specificity-ordered resolution and collector isolation; adapt reason enum values to your domain; omit MCP_ERROR plumbing if you have no MCP tools.
