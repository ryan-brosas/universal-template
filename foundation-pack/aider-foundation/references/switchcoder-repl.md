<!-- capsule-v2 -->
# SwitchCoder REPL — exception-as-control-flow coder hot-swap preserving IO and chat state

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a long-lived CLI swap its edit-format/coder object mid-session (user runs `/model`, `/architect`, `/chat-mode`) without losing the terminal, history, or repo bindings?

## Raise out of run(); rebuild the coder in the outer loop
**Path/Symbol:** `aider/main.py` main REPL (:1159-1181); `SwitchCoder` raised by `aider/commands.py` handlers; exactly TWO catch sites: `--message` one-shot swallow (:1131) and the REPL loop (:1165).
**Signature:** `kwargs = dict(io=io, from_coder=coder); kwargs.update(switch.kwargs)` → `coder = Coder.create(**kwargs)`.
**Data Shape:** `SwitchCoder(kwargs..., placeholder=None)`; `io.placeholder` carries a pending user prompt across the swap.

### Decisive source
```python
while True:
    try:
        coder.ok_to_warm_cache = bool(args.cache_keepalive_pings)
        coder.run()
        return
    except SwitchCoder as switch:
        coder.ok_to_warm_cache = False
        if hasattr(switch, "placeholder") and switch.placeholder is not None:
            io.placeholder = switch.placeholder
        kwargs = dict(io=io, from_coder=coder)
        kwargs.update(switch.kwargs)
        if "show_announcements" in kwargs:
            del kwargs["show_announcements"]
        coder = Coder.create(**kwargs)
        if switch.kwargs.get("show_announcements") is not False:
            coder.show_announcements()
```

**Flow:** command handlers raise `SwitchCoder(edit_format=..., main_model=...)` instead of returning a new coder → outer loop catches, seeds kwargs with the LIVE io + old coder (`from_coder` lets the new instance inherit chat history/abs_fnames), strips an explicit `show_announcements=False` key, creates the replacement, re-announces unless suppressed → loop re-enters `run()` on the new object.
**Invariant:** the REPL is the ONLY place a coder is replaced during an interactive session; the scripted `--message` path treats a SwitchCoder as "ignore and finish" so batch runs can never silently restart into interactive mode; `ok_to_warm_cache` is force-cleared during swaps so a dying coder doesn't fire cache-keepalive pings.
**Probe:** deterministic: `grep -c 'except SwitchCoder' aider/main.py` → 2 (:1131 bare swallow in the `--message` arm; :1165 `as switch` REPL handler). Direct tests: `tests/basic/test_commands.py` exercises command-layer switches through Commands.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "guessed_wrong_repo SwitchCoder", limit: 3 });
// rank-1: guessed_wrong_repo aider/main.py 69-85 (the other recursion driver)
```

## Verdict
Adopt the exception-as-hot-swap REPL shape for any multi-mode agent shell; adapt the analytics reasons. Omit nothing — the lone `--message` swallow-site is the part porters miss, and it is what keeps CI-style runs one-shot.
