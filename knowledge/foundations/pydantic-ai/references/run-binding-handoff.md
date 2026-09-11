<!-- capsule-v2 -->
# RunBinding: handle-before-run cancellation ownership

## Source / Question
`pydantic_ai_slim/pydantic_ai/run.py` + `_cancel.py` — How does pydantic-ai let an `AgentRunEvents` handle (which exists before its lazy background run) own cancellation, and how does the run attach its live state without losing that controller? A porter must know the binding handoff and the consume-once rule.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/run.py` — `AgentRun` (31), `AgentRun.cancel` (555). `pydantic_ai_slim/pydantic_ai/_cancel.py` — `RunBinding` (260–268), `provide_run_binding` (275–282), `take_run_binding` (285–293), `_current_run_binding` ContextVar (272). `pydantic_ai_slim/pydantic_ai/agent/__init__.py` — `take_run_binding()` call (1309).

## Signature
```python
@dataclasses.dataclass
class RunBinding:
    cancellation: RunCancellation = field(default_factory=RunCancellation)
    agent_run: AgentRun | None = None

@contextmanager
def provide_run_binding(binding: RunBinding) -> Generator[None]
def take_run_binding() -> RunBinding | None
```

## Data Shape
`_current_run_binding: ContextVar[RunBinding | None]` (default None). `RunBinding` pairs the cancellation controller with the (initially absent) live `AgentRun`.

## Decisive source
`RunBinding` docstring (260–268): "The handle exists before its lazy background run, so it owns the cancellation controller. `Agent.iter()` later attaches the live run state while retaining that same controller." `take_run_binding` (285–293): consumes the pending binding at most once — setting the ContextVar to None prevents nested agent runs from inheriting the outer handle's binding.

## Flow / Invariant
1. **Handle-first ownership**: the `AgentRunEvents` handle is created before its lazy background run starts; it owns the `RunCancellation` controller.
2. **ContextVar handoff**: `provide_run_binding` sets the binding for runs started in that context (reset on exit); `Agent.iter()` calls `take_run_binding()` (agent/__init__.py:1309) to attach the live run state to the SAME controller.
3. **Consume-once**: `take_run_binding` nulls the ContextVar so a nested agent run started inside the outer run does NOT inherit the outer handle's binding — each run gets its own cancellation identity.
4. The controller is runtime-only state (holds a live task reference), never serialized.

## Probe (direct test)
`tests/test_run_cancellation.py`: `test_cancellation_token_from_sibling_task` (:164), `test_one_token_cancels_two_runs` (:200), `test_token_accepted_by_iter_and_stream_surfaces` (:232), `test_agent_run_cancel_from_another_task` (:486).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'RunBinding take_run_binding'` → `_cancel.RunBinding` (260–268), `take_run_binding` (285–293).

## Verdict
**Adopt** the binding-handoff pattern for any lazy-run API surface where a handle precedes execution — the controller must be owned by the earliest-created object and handed to the run by reference, with consume-once to isolate nested runs.
