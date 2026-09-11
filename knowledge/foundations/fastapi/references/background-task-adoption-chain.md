<!-- capsule-v2 -->
# Background task adoption chain — How do tasks declared in dependencies reach the response that runs them after send?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** Through which hand-offs does a `BackgroundTasks` object travel from a nested dependency to post-response execution, and when does a returned Response keep its own background?

## Single shared StarletteBackgroundTasks threaded through solve
**Path/Symbol:** `fastapi/dependencies/utils.py:solve_dependencies` (715–718: lazy instantiation; 652: adoption from child solves) + `fastapi/routing.py:_build_response_args` (357–372) + raw-Response branch (711–714).
**Signature:** parameter `background_tasks: StarletteBackgroundTasks | None = None` threaded through every recursive level; `SolvedDependency.background_tasks`.
**Data Shape:** FastAPI's `BackgroundTasks` subclasses Starlette's purely for typing/docs — execution semantics are Starlette's: FIFO `add_task`, run after the response completes.

### Decisive source
```python
        background_tasks = solved_result.background_tasks      # adopt from sub-solve
        ...
    if dependant.background_tasks_param_name:
        if background_tasks is None:
            background_tasks = BackgroundTasks()               # create ONCE, lazily
        values[dependant.background_tasks_param_name] = background_tasks
```
```python
def _build_response_args(*, status_code, solved_result):
    response_args = {"background": solved_result.background_tasks}
```
and on a user-returned Response:
```python
                if isinstance(raw_response, Response):
                    if raw_response.background is None:
                        raw_response.background = solved_result.background_tasks
```

**Flow:** any dependency (at any depth) or the endpoint declaring `background_tasks: BackgroundTasks` receives THE SAME instance → tasks added anywhere run once, after the final response is sent → `_build_response_args` passes the collection into whichever Response gets constructed → a handler-returned Response adopts the collection only when it doesn't already carry one.
**Invariant:** (1) The instance must be created lazily and shared — creating per-dependency would silently drop sibling tasks. (2) An explicitly set `Response(background=...)` WINS; solved tasks are not merged. (3) Streaming/SSE branches also route through `_build_response_args`, so background tasks fire only after the stream finishes.
**Probe:** `tests/test_background_tasks.py` (+ dependency-declared variants) pin ordering: response body first, then tasks in FIFO order.
