<!-- capsule-v2 -->
# TaskCompletionOutcome (typed terminal outcome parsed from the result, not the loop)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** Where does the shape of "the run is done, here's what to return" live so new terminal tools need zero loop edits — and why there?

## Path/Symbol
`tools/builtin/planning/task_complete.py` — `TaskCompletionOutcome` dataclass (:12–38), `TaskCompleteTool.extract_outcome(tr, call, fallback_text)` staticmethod (:146–208). Consumed by `agent/tool_loop.py::TerminalTool` protocol (:32–41) and its post-result branch (:381–398).

## Signature
`TaskCompletionOutcome(task_done, final_output=None, artifacts=[], confidence=None, record_ids=[], needs_input=None, error_result: CoreToolResult | None = None)`. The dataclass is deliberately colocated with the tool that defines the payload's shape; `agent/tool_loop.py` imports it ONE-WAY (no cycle).

## Data Shape
Input: successful terminal ToolResult content dict + the turn's own response text as fallback. Output fields map 1:1 onto `AgentResult`'s typed sub-agent contract. `error_result != None` means REJECT the whole call: return it as the tool's error result instead of completing.

### Decisive source
```python
if not str(final_output).strip():
    # Neither an output argument nor response text — completing now would
    # return nothing to the caller.
    return TaskCompletionOutcome(
        task_done=False,
        error_result=CoreToolResult(...,
            content=("task_complete was called with an empty `output` and "
                     "there was no response text to fall back on — ..."),
            is_error=True),
    )
```

**Flow:** loop sees non-error result of a TAG_LIFECYCLE_TERMINAL-tagged tool → resolves it → `isinstance(tool, TerminalTool)` duck-check → `tool.extract_outcome(tr, call, agent.extract_text(response_msg))` → maps to ToolCallOutcome (task_done/final_output/artifacts/confidence/record_ids/needs_input). Empty output + no fallback ⇒ error_result bounce forcing a re-call; malformed artifact dicts DROPPED not fatal (:177–185); out-of-enum confidence dropped (:187–195); blank record_ids filtered; blank needs_input normalized to None (:202–203). Some models write the full answer as response text and forget the arg — hence the fallback_text ladder (:158).

**Invariant:** Terminality dispatches on TAG + protocol, never on tool NAME (`call.name == "task_complete"` appears nowhere) — a future terminal tool is tag + extract_outcome only. Malformed optional fields degrade individually; ONLY a would-be-empty completion rejects. needs_input NEVER overrides task_done/final_output (it flags escalation on top of a normal completion).

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/planning/test_task_complete.py` — defaults :20, case-insensitive confidence :32, invalid-confidence-dropped :38, non-list record_ids ignored :51, blank needs_input→None :74; empty-output bounce pinned in agent/test_task_complete_output_contract.py.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["TaskCompletionOutcome","extract_outcome","TerminalTool"]'
```

## Verdict
Adopt the outcome-dataclass + tag/protocol terminality split (loop owns stop mechanics; tool owns payload semantics). Adapt field set to host's AgentResult. Omit pipeshub-specific env gates. Extends (does not replace) the earlier terminal-tool-contract capsule: that one pins the loop's detection half, this one the tool-side parsing half.
