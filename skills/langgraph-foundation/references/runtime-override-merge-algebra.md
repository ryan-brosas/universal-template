<!-- capsule-v2 -->
# Runtime override/merge algebra — How does the engine compose per-run and per-task runtime objects (context, store, stream writer, heartbeat, execution info) without mutating shared state?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A node's `Runtime` must reflect the parent run's context/store/writer while carrying task-specific execution info and (under timeouts) guarded writer/heartbeat — what are the composition rules that make this safe?

## Frozen dataclass; two operators with different precedence rules; sentinel identity checks protect the writer
**Path/Symbol:** `libs/langgraph/langgraph/runtime.py:Runtime.merge` (:240-258), `Runtime.override` (:260-264), `Runtime.patch_execution_info` (:266-274), no-op sentinels `_no_op_stream_writer`/`_no_op_heartbeat` (:107-110), `RunControl` (:79-104); usage: `pregel/main.py` (:2881, :3324 parent merge), `pregel/_algo.py` (:691, :883, :1045, :1194 prep overrides), `pregel/_retry.py:_TimedAttemptScope.wrap_config` (:178-187 guard override).
**Signature:** `@dataclass(kw_only=True, slots=True, frozen=True) class Runtime(Generic[ContextT])`; `merge(self, other: Runtime[ContextT]) -> Runtime[ContextT]`; `override(self, **overrides: Unpack[_RuntimeOverrides[ContextT]]) -> Runtime[ContextT]` (plain `dataclasses.replace`).
**Data Shape:** Fields: `context`, `store`, `stream_writer` (default = module-level no-op function), `heartbeat` (default = module-level no-op), `previous`, `execution_info`, `server_info`, `control`. Merge precedence: `other` wins for every field, EXCEPT `stream_writer`/`heartbeat` use IDENTITY checks against the no-op sentinels (`is not _no_op_stream_writer` / `is not _no_op_heartbeat`) so a default no-op can never clobber a real one; `context`/`store`/`execution_info`/`server_info`/`control` use truthiness (`or`); `previous` uses an explicit None check.

### Decisive source
```python
    def merge(self, other: Runtime[ContextT]) -> Runtime[ContextT]:
        return Runtime(
            context=other.context or self.context,
            store=other.store or self.store,
            stream_writer=other.stream_writer
            if other.stream_writer is not _no_op_stream_writer
            else self.stream_writer,
            heartbeat=other.heartbeat
            if other.heartbeat is not _no_op_heartbeat
            else self.heartbeat,
            previous=self.previous if other.previous is None else other.previous,
            execution_info=other.execution_info or self.execution_info,
            server_info=other.server_info or self.server_info,
            control=other.control or self.control,
        )
```

**Flow:** At stream start the engine builds a fresh child `Runtime` (coerced context, store, resolved stream writer, `control=control or parent_runtime.control or RunControl()`) and merges it INTO the parent runtime (`parent_runtime.merge(runtime)`) before storing it in config — this is how a subgraph inherits the parent's custom writer. Each of the four task-prep paths then `override`s `previous`/`store`/`execution_info` onto the per-task copy; under a timeout policy, `_TimedAttemptScope.wrap_config` overrides `stream_writer` with its guarded wrapper and sets `heartbeat=self.touch`. Nodes receive the composed object; no original instance is ever mutated (frozen dataclass). `patch_execution_info` raises RuntimeError when `execution_info` is None — fail-loud before task preparation populates it. `RunControl.request_drain` is a single attribute write: the drain signal is lock-free by construction, and `merge` carries `control` forward so draining propagates to subgraphs.
**Invariant:** A default no-op writer/heartbeat can never clobber a real one during merge (identity, not truthiness); all composition returns new instances; `override` is exact replacement with no precedence logic; drain state survives merge into child runtimes.
**Probe:** `python -m pytest "tests/test_runtime.py::test_override_runtime" "tests/test_runtime.py::test_merge_runtime" "tests/test_runtime.py::test_merge_runtime_preserves_run_control" "tests/test_runtime.py::test_run_control_request_drain_stops_future_steps" -q` — 4 passed (merge applies only non-falsy values; control identity preserved across merge; request_drain stops future steps). Byte-exact: `grep -c "if other.stream_writer is not _no_op_stream_writer" libs/langgraph/langgraph/runtime.py` → 1; `grep -c "Cannot patch execution_info before it has been set" .../runtime.py` → 1; `grep -c "def merge(self, other: Runtime\[ContextT\])" .../runtime.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "Runtime override merge stream_writer heartbeat no-op sentinel patch_execution_info", limit: 8 });
```

## Verdict
Adopt the frozen-dataclass + two-operator split: `merge` for "child inherits parent, filling only what it provides" (with sentinel-identity checks for any field whose default is a callable no-op — truthiness is wrong there), `override` for exact per-task replacement. Adopt fail-loud patching when a field has a well-defined population point. Adapt the field set to your host's run-scoped dependencies; omit server-injected metadata fields unless you have a deployment plane. Keep drain as a single lock-free write if your shutdown protocol is cooperative.
