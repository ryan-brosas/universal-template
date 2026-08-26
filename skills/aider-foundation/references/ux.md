<!-- capsule-v2 -->
# Human I/O — batch-scoped confirmations, never-prompts, interrupt safety

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a terminal harness ask for consent without nagging, batch the same decision across many files, and survive interrupts without losing the user's input?

## Confirmation cascade, group replay, and prompt safety
**Path/Symbol:** `aider/io.py`: `InputOutput.confirm_ask(question, default="y", subject=None, explicit_yes_required=False, group=None, allow_never=False)` (:807), `ConfirmGroup` (:82), `never_prompts` (:269), `restore_multiline` (:57), `get_input` (:523).
**Signature:** `confirm_ask(...) -> bool`.
**Data Shape:** routes through never-prompt set → `self.yes` tri-state → group.preference replay → interactive input; a `ConfirmGroup` shared across per-file confirms posts an all/skip decision to `preference`; `never_prompts` is a `(question, subject)` set.

### Decisive source
```python
if question_id in self.never_prompts:
    return False
if group and not group.show_group:
    group = None
if group:
    allow_never = True
if self.yes is True:
    res = "n" if explicit_yes_required else "y"   # blanket yes downgraded when unsafe
elif group and group.preference:
    res = group.preference
else:
    while True:  # interactive; EOF degrades to default, any unambiguous prefix accepted
        res = res.lower()[0]
        if res == "d" and allow_never:
            self.never_prompts.add(question_id)  # (question, subject) tuple
```

**Flow:** resolve never-prompt; demote single-item groups and force allow_never when a group is active; resolve capped yes/no; shared group preference short-circuits; otherwise loop interactively; normalize any unambiguous prefix to its first char; record a permanent in-process dismissal on `d`; wrap inner prompts with `restore_multiline` so a confirm mid-composition forces single-line and restores it in finally.
**Invariant:** group confirmations present the decision once per set; `explicit_yes_required` overrides blanket yes and hides `(A)ll`; `never_prompts` keys on `(question, subject)` so a file dismissal never silences another; nested prompts cannot leak a changed multiline mode.
**Probe:** `tests/basic/test_io.py::test_confirm_ask_with_group` (after preference="all", `mock_input.assert_not_called()`), `test_confirm_ask_explicit_yes_required` (assertNotIn("(A)ll", prompt_text)), `test_multiline_mode_restored_after_interrupt`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "confirm_ask ConfirmGroup never_prompts restore_multiline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-preference confirmation object and the `(question, subject)` never-set as the safe consent model: ask once, remember the group decision, key dismissals by (question, subject), and make destructive paths explicit-yes. Adapt rendering to the host; omit Aider's exact prompt strings.
