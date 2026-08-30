<!-- capsule-v2 -->
# Reply-driving pipeline — one choke point ordering retries, exhaustion, interrupts, edits, lint, shell, tests

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** In a single agent turn, how must post-reply side effects be ordered so each failure class produces at most one reflection and the transcript stays alternation-valid?

## send_message: bounded retry algebra inside, strict effect order outside
**Path/Symbol:** `aider/coders/base_coder.py`: `Coder.send_message(inp)` (:1419-1623). Reflection cap itself lives in `run_one` (capsule'd in collab.md).
**Signature:** generator-free driver: consumes `self.send(messages)` chunks, mutates `cur_messages`, sets `reflected_message` or applies edits.
**Data Shape:** `retry_delay = 0.125` doubling until `RETRY_TIMEOUT` (imported from aider.models); flags `exhausted` / `interrupted`; `partial_response_content` finalized in `finally`.

### Decisive source
```python
while True:
    try:
        yield from self.send(messages, functions=self.functions)
        break
    except litellm_ex.exceptions_tuple() as err:
        if ex_info.name == "ContextWindowExceededError":
            exhausted = True; break                      # no retry possible
        should_retry = ex_info.retry
        if should_retry:
            retry_delay *= 2
            if retry_delay > RETRY_TIMEOUT: should_retry = False
        if not should_retry:
            self.check_and_open_urls(err, ex_info.description); break
        time.sleep(retry_delay); continue
    except KeyboardInterrupt:
        interrupted = True; break
    except FinishReasonLength:
        if not self.main_model.info.get("supports_assistant_prefill"):
            exhausted = True; break
        # continuation: resume as assistant prefill
        messages.append(dict(role="assistant",
                       content=self.multi_response_content, prefix=True))
...
if not interrupted:
    add_rel_files_message = self.check_for_file_mentions(content)
    if add_rel_files_message:
        self.reflected_message = add_rel_files_message; return   # mention turn short-circuits
    if self.reply_completed(): return
edited = self.apply_updates()
if edited:
    self.aider_edited_files.update(edited)
    saved_message = self.auto_commit(edited)
    self.move_back_cur_messages(saved_message)
if edited and self.auto_lint:
    lint_errors = self.lint_edited(edited)
    self.auto_commit(edited, context="Ran the linter")           # SECOND commit
    if lint_errors and confirm: self.reflected_message = lint_errors; return
shared_output = self.run_shell_commands()   # appended as user/"Ok" pair
...auto_test same shape with cmd_test...
```

**Flow:** retry loop (transient errors double-backoff; context-window => exhausted; output-limit => assistant prefill continuation when the model supports it, else exhausted; interrupt => flag; unknown exception => traceback + analytics event + silent return) -> `finally` ALWAYS finalizes partial content, flushes mdstream, stops spinner -> mentions gate -> `reply_completed` hook -> apply edits -> auto-commit edited paths -> move assistant/history messages back -> auto-lint (own commit "Ran the linter"; failures reflect only after confirm) -> shell output as user+"Ok" message pair -> auto-test same shape.
**Invariant:** exhausted/interrupted turns inject synthetic ASSISTANT messages ("FinishReasonLength exception…", "^C KeyboardInterrupt" marker rewritten onto the last USER message plus an ack) so strict role alternation survives every early exit; a mention-add always costs exactly one turn before any edit application; each of lint/shell/test may set `reflected_message` at most once per turn — the cap lives upstream in run_one.
**Probe:** `tests/basic/test_sendchat.py` pins the retry/alternation primitives (12 passed this run); `tests/basic/test_coder.py::test_show_exhausted_error` (:1095); mention-gate behavior pinned by the five `*file_mentions*` coder tests. Deterministic anchors: `grep -nF 'retry_delay = 0.125'` -> :1449; `grep -nF 'Ran the linter'` -> :1601; `grep -nF '^C KeyboardInterrupt'` -> :1577.
**Coverage caveat:** no single direct test executes the full post-reply ordering end-to-end; the ordering claims above are anchor-verified against source and surrounded by the executed suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "send_message", limit: 3 });
// resolves Coder.send_message :1419-1623 rank-1
```

## Verdict
Adopt the effect ORDER (mentions -> hook -> edits -> commit -> lint(+second commit) -> shell -> test) and the alternation-preserving synthetic messages as the pipeline contract. Adapt confirmation UX, event names, and backoff constants; omit Aider's prompt templates. Porters who reorder lint before commit lose the "Ran the linter" audit trail that makes /undo meaningful.
