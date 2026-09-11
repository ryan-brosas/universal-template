<!-- capsule-v2 -->
# Command reflection dispatch — how does a REPL expose commands with zero registry and still resolve prefixes safely?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a console own 43 slash-commands without a registration table, resolve ambiguous prefix typing, and keep one command's failure from killing the loop?

## The class body is the command registry
**Path/Symbol:** `aider/commands.py`: `Commands.get_commands` (:276-285), `Commands.matching_commands` (:300-310), `Commands.run` (:312-332), `Commands.do_run` (:287-298).
**Signature:** `get_commands(self) -> list[str]`; `run(self, inp)`; `do_run(self, cmd_name, args)`.
**Data Shape:** input is the raw typed line (`/cmd rest` or `!shell`); output is whatever the command method returns. Command names are `cmd_xxx` methods → `/xxx` (`_`→`-`). Completions follow by convention: `completions_<cmd>()`, `completions_raw_<cmd>()`.

### Decisive source
```python
def run(self, inp):
    if inp.startswith("!"):
        self.coder.event("command_run")
        return self.do_run("run", inp[1:])
    res = self.matching_commands(inp)
    ...
    if len(matching_commands) == 1:
        command = matching_commands[0][1:]
        ...return self.do_run(command, rest_inp)
    elif first_word in matching_commands:
        command = first_word[1:]
        ...return self.do_run(command, rest_inp)
    elif len(matching_commands) > 1:
        self.io.tool_error(f"Ambiguous command: {', '.join(matching_commands)}")
```

**Flow:** `!` bypasses matching entirely → shell passthrough. Otherwise: unique prefix match executes; several prefix matches but one EQUALS the typed word exactly → that one wins over its prefix siblings; otherwise "Ambiguous command" lists every match (or "Invalid command"). `do_run` maps `-`→`_`, uses `getattr(self, name, None)` so a vanished command prints an error instead of raising, and wraps EVERY dispatch in `except ANY_GIT_ERROR`.
**Invariant:** no git-layer exception may ever escape a command into the REPL loop; mode-switching commands escape via `SwitchCoder` (exception-as-control-flow), which is caught only at designated swallow sites.
**Probe:** deterministic: DSH grep `^    def cmd_` on `aider/commands.py` → **43 matches** (the whole registry); `ANY_GIT_ERROR` in the same file → **7 matches**, including the dispatch wrapper at :297. Direct tests: `.venv/bin/python -m pytest tests/basic/test_commands.py -k 'test_cmd_add or test_cmd_tokens_output or save_and_load' -q` → **26 passed** (executed this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "matching_commands", limit: 10 });
// rank-2: aider.aider.commands.Commands.matching_commands aider/commands.py 300-310 (get_commands rank-1 :276-285)
```

## Verdict
Adopt reflection-as-registry for plugin-style command surfaces and the exact-over-prefix resolution rule (it makes `/lo` unambiguous the moment `/load` exists). Adapt the error channel and event names to your host. Omit aider's SwitchCoder coupling unless you port the coder hot-swap too. Caveat: exact-over-prefix behavior is source-pinned; no dedicated upstream test asserts it directly.
