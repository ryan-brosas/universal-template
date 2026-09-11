<!-- capsule-v2 -->
# Batch-mode one-shot ladder — --lint/--test/--commit/--message/--apply early-exit matrix

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does one binary serve both a REPL and a scriptable batch tool without the two modes leaking into each other?

## Ordered early-exit ladder: each batch flag runs its action through the coder/commands layer then RETURNS; --message is the terminal arm
**Path/Symbol:** `aider/main.py` post-create ladder: `--show-prompts` (:1044-1051), `--lint` (:1053-1054), `--test` (+placeholder replay :1056-1063), `--commit` (:1065-1069), combined exit :1071-1073, `--show-repo-map` (:1075-1080), `--apply` (:1082-1093), `--message` (:1126-1134), `--message-file` (:1136-1151), `--exit` (:1153-1155).
**Signature:** every arm funnels through `coder.commands.cmd_*` or `coder.run(with_message=...)`; lint/test/commit arms end with `analytics.event("exit", reason="Completed lint/test/commit"); return`.
**Data Shape:** `--test` requires an explicit test_cmd (error + exit 1 if absent); after cmd_test, a pending `io.placeholder` triggers ONE `coder.run(io.placeholder)` — test failures become a chat turn.

### Decisive source
```python
if args.test:
    if not args.test_cmd:
        io.tool_error("No --test-cmd provided.")
        return 1
    coder.commands.cmd_test(args.test_cmd)
    if io.placeholder:
        coder.run(io.placeholder)
...
if args.message:
    io.add_to_input_history(args.message)
    try:
        coder.run(with_message=args.message)
    except SwitchCoder:
        pass
    return
```

**Flow:** flags compose left-to-right (`--lint --test --commit` runs all three) but NEVER fall into the REPL — the combined guard returns before interactive setup (watchers, announcements). `--apply` reads a file INTO partial_response_content and calls apply_updates() directly, bypassing any LLM call. `--exit` still constructs everything (so cache warming + announcements happen) then quits.
**Invariant:** batch mode is read-only w.r.t. session state — no FileWatcher, no ClipboardWatcher, no warm-cache loop; the only feedback channel back into the chat is the test-placeholder replay, which fires at most once.
**Probe:** deterministic anchors: `grep -nF 'cmd_test' aider/main.py` → :1061; `grep -nF 'Completed lint/test/commit' aider/main.py` → :1072. Direct tests: `tests/basic/test_main.py` covers --message/--exit/--apply arms (executed green within the basic-suite run below).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "args.test cmd_test placeholder", limit: 3 });
// resolves main.py batch ladder sites
```

## Verdict
Adopt the ordered-ladder shape for dual REPL/batch CLIs: shared construction, mode-specific exits, explicit analytics per exit reason. Porters who let batch flags fall through to the REPL hang CI pipelines — the combined-return guard is the load-bearing line.
