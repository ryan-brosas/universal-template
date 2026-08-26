<!-- capsule-v2 -->
# Editor roundtrip pipeline — how does a terminal tool hand a buffer to the user's editor and get text back safely?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you honor VISUAL/EDITOR/platform defaults, support editors with quoted arguments, and never lose or leak the temp file even when the environment is hostile?

## Temp-file roundtrip with shell-split arguments
**Path/Symbol:** `aider/editor.py`: `get_environment_editor` (:70-86), `discover_editor` (:89-112), `write_temp_file` (:41-67), `pipe_editor` (:115-147); consumers `Commands.cmd_editor`/`cmd_edit` (commands.py).
**Signature:** `pipe_editor(input_data="", suffix=None, editor=None) -> str`; `write_temp_file(input_data="", suffix=None, prefix=None, dir=None) -> str`; `discover_editor(editor_override=None) -> str`.
**Data Shape:** content in → same-or-edited content out; one mkstemp file per call; editor resolved as a single COMMAND STRING (not argv list).

### Decisive source
```python
editor = os.environ.get("VISUAL", os.environ.get("EDITOR", default))   # :85 nested fallback
...
command_str = discover_editor(editor)
command_str += " " + filepath
subprocess.call(command_str, shell=True)          # :134 shell=True IS the arg parser
with open(filepath, "r") as f:
    output_data = f.read()                        # exit code deliberately ignored
try:
    os.remove(filepath)
except PermissionError:                            # :139 warn-only cleanup
    print_status_message(False, "... You may need to delete it manually.")
```

**Flow:** precedence override arg > VISUAL > EDITOR > platform default (Windows=notepad, Darwin=vim, else vi). `write_temp_file` mkstemp+fdopen; if the write raises it closes the fd manually before re-raising (:62-66, no fd leak). `pipe_editor` appends the filepath to the command STRING and invokes it via `shell=True` — quoted editor args like `vim -c "set noswapfile"` work only because a shell splits them (`discover_editor` does no parsing despite its docstring). The subprocess return code is ignored: content is read back unconditionally, so an editor that crashes without saving degrades to a no-op roundtrip. Cleanup failure downgrades to a warning; edited content is still returned.
**Invariant:** the user's in-editor work is never lost to launch/cleanup failures — every failure mode (fd write error, editor crash, undeletable temp) either re-raises before the editor runs or returns the best available content with a warning. Suffix is dot-prefixed once (`f".{suffix}"`) so syntax highlighting works in arbitrary editors.
**Probe:** `.venv/bin/python -m pytest tests/basic/test_editor.py -q` → **7 passed** (executed this pass), incl. `test_pipe_editor_with_fake_editor` asserting the editor receives a `.md` temp path and `test_pipe_editor` forcing `os.remove` PermissionError while content survives.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "pipe_editor", limit: 10 });
// rank-1: aider.aider.editor.pipe_editor aider/editor.py 115-147 (inbound callers: Commands.cmd_edit, cmd_editor)
```

## Verdict
Adopt the string-command + shell=True contract ONLY for trusted local editor config (it is an intentional eval surface, like a shell alias); adopt the fd-close-on-failure temp writer and warn-only cleanup universally. Adapt platform defaults to your host. Omit the ignored-exit-code behavior if your callers must distinguish "user saved" from "user aborted" — detect it yourself by comparing content.
