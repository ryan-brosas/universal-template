<!-- capsule-v2 -->
# Command navigation writes — How do node-returned Commands become graph navigation?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** What is the complete write grammar that translates `Command(goto=..., resume=..., update=...)` at node-return and loop-input positions?

## Exactly three navigation verbs: TASKS write, branch:to write, upward exception
**Path/Symbol:** `libs/langgraph/langgraph/graph/state.py:_control_branch` (:1749-1775), `libs/langgraph/langgraph/pregel/_io.py:map_command` (:56-78).
**Signature:** `_control_branch(value: Any) -> Sequence[tuple[str, Any]]` (node-return position); `map_command(cmd: Command) -> Iterator[tuple[str, str, Any]]` (loop-input position, yields `(NULL_TASK_ID, channel, value)` pending writes).
**Data Shape:** goto accepts one or a sequence of `Send | str`; `update` expands via `cmd._update_as_tuples()`; resume rides a `(NULL_TASK_ID, RESUME, cmd.resume)` write.

### Decisive source
```python
# _control_branch — node-return position:
def _control_branch(value: Any) -> Sequence[tuple[str, Any]]:
    if isinstance(value, Send):
        return ((TASKS, value),)
    commands: list[Command] = []
    if isinstance(value, Command):
        commands.append(value)
    elif isinstance(value, (list, tuple)):
        for cmd in value:
            if isinstance(cmd, Command):
                commands.append(cmd)
    rtn: list[tuple[str, Any]] = []
    for command in commands:
        if command.graph == Command.PARENT:
            raise ParentCommand(command)
        for go in ([command.goto] if isinstance(command.goto, (Send, str)) else command.goto):
            if isinstance(go, Send):
                rtn.append((TASKS, go))
            elif isinstance(go, str) and go != END:
                # END is a special case ... we don't need to branch to
                rtn.append((_CHANNEL_BRANCH_TO.format(go), None))
    return rtn
```
```python
# _io.map_command — loop-input position yields NULL_TASK_ID pending writes:
    if cmd.graph == Command.PARENT:
        raise InvalidUpdateError("There is no parent graph")
    if cmd.goto:
        for send in sends:
            if isinstance(send, Send):   yield (NULL_TASK_ID, TASKS, send)
            elif isinstance(send, str):  yield (NULL_TASK_ID, f"branch:to:{send}", START)
    if cmd.resume is not None:           yield (NULL_TASK_ID, RESUME, cmd.resume)
```

**Flow:** A node returns `Send` / `Command` / sequence of Commands -> `_control_branch` reduces it during the task's control phase: Sends become TASKS-channel writes (dynamic fan-out next superstep), goto strings become `branch:to:<node>` trigger writes (the SAME mechanism compiled conditional edges use), `graph == PARENT` raises `ParentCommand` so the retry/bubble-up ladder carries it to the parent graph (see retry-parentcommand-ladder capsule), and END gotos are silently dropped. The same grammar appears at loop INPUT via `map_command`: user-supplied `Command(resume=...)` injects the RESUME write under NULL_TASK_ID, `goto` seeds TASKS/branch channels before any task runs, and PARENT at top level is InvalidUpdateError because there is no parent.
**Invariant:** Navigation never mutates the task graph — it is expressed purely as channel writes plus one exception type. Resume values and goto share the NULL_TASK_ID pending-write lane so they apply before task preparation. A Command carrying BOTH goto and update fans into independent write tuples atomically.
**Probe:** `python -m pytest tests/test_retry.py::test_checkpoint_ns_for_parent_command -q` (PARENT upward leg naming); `grep -n "NULL_TASK_ID" libs/langgraph/langgraph/pregel/_io.py` → 5 hits (:10 import; write-yield sites :67,:69,:75,:78).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "_control_branch map_command ParentCommand goto", limit: 8 });
```

## Verdict
Adopt the three-verb grammar — it keeps navigation inspectable as ordinary writes and replayable from checkpoints. Adapt the synthetic channel name template and the PARENT detection key to your host. Omit tuple-of-Commands support only if your host nodes cannot return sequences; keep the silent-END-drop semantics either way.
