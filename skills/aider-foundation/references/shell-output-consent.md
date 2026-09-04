<!-- capsule-v2 -->
# Shell-output consent (run-shell boundary)

**Source:** Aider Apache-2.0 `main@5dc9490b...`; Codebase Memory project `aider` (full). **Question:** How does a harness run Bash suggested by the model without ever executing silently or auto-admitting its output to chat?

## Two independent consent gates
**Path/Symbol:** `Coder.handle_shell_commands` (base_coder.py:2450-2485); `Commands.cmd_run` (commands.py:1013-1053).
**Signature:** `handle_shell_commands(commands_str, group) -> str | None`.
**Data Shape:** newline-delimited proposed commands; an explicit-yes confirmation; labelled accumulated stdout/stderr.

### Decisive source
```python
if not self.io.confirm_ask(prompt, subject="\n".join(commands), explicit_yes_required=True, group=group, allow_never=True): return
...
if accumulated_output.strip() and self.io.confirm_ask("Add command output to the chat?", allow_never=True):
    return accumulated_output
```

**Flow:** extract proposed shell blocks; show the exact batch and require explicit consent before any execution; run accepted commands in the workspace root; accumulate labelled output; separately ask before output enters chat.
**Invariant:** a model suggestion never executes without explicit consent, and executing never implies chat admission. Host must replace Aider `shell=True`.
**Probe:** `tests/basic/test_coder.py::TestCoder.test_suggest_shell_commands` (:975); `test_run_cmd.py::test_run_cmd_echo` (:6). Direct test runner unavailable; inspected source tests only.

## Retrieve
`search_graph({ project: "aider", query: "handle_shell_commands" })`

## Verdict
Two independent consent boundaries: one for execution, one for chat admission.
