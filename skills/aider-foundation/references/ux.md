<!-- capsule-v2 -->
# Human I/O — batch-scoped confirmations, never-prompts, interrupt safety

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a terminal harness ask for consent without nagging, batch the same decision across many files, and survive interrupts without losing the user's input?

## Confirmation cascade, group replay, and prompt safety
**Path/Symbol:** `aider/io.py`: `InputOutput.confirm_ask(question, default="y", subject=None, explicit_yes_required=False, group=None, allow_never=False)` (:807), `ConfirmGroup` (:82), `never_prompts` (:269), `restore_multiline` (:57), `get_input` (:523).
**Signature:** `confirm_ask(...) -> bool`.
**Data Shape:** routes through never-prompt set → `self.yes` tri-state → group.preference replay → interactive input; a `ConfirmGroup` shared across per-file confirms posts an all/skip decision to `preference`; `never_prompts` is a `(question, subject)` set.

### Decisive source
```python
question_id = (question, subject)
if question_id in self.never_prompts:
    return False                              # :823-824 keyed on the TUPLE, first-return
if group and not group.show_group:
    group = None                              # :826-827 single-item group demotes
if group:
    allow_never = True                        # :828-829 any group forces don't-ask option

valid_responses = ["yes", "no", "skip", "all"]
...
if self.yes is True:
    res = "n" if explicit_yes_required else "y"   # :866-867 blanket yes downgraded when unsafe
elif self.yes is False:
    res = "n"
elif group and group.preference:
    res = group.preference
    self.user_input(f"{question}{res}", log_only=False)   # :870-872 REPLAY echoes the decision
else:
    while True:
        try: ...prompt/input...
        except EOFError:
            res = default                     # :884-887 EOF (Ctrl+D) degrades to default
            break
        if not res:
            res = default                     # :889-891 blank input also defaults
            break
        res = res.lower()
        good = any(valid_response.startswith(res) for valid_response in valid_responses)
        if good:                              # :892-895 UNAMBIGUOUS-PREFIX ladder validates
            break
        self.tool_error(f"Please answer with one of: {', '.join(valid_responses)}")

res = res.lower()[0]                          # :900 truncation happens AFTER validation
```

**Flow:** resolve never-prompt; demote single-item groups and force allow_never when a group is active; resolve capped yes/no; shared group preference short-circuits AND echoes the answered question through `user_input(log_only=False)` so transcripts show it even though nothing was asked; otherwise loop interactively — EOF and blank both degrade to default, any unambiguous prefix of yes/no/skip/all/don't validates, ambiguous prefixes re-prompt listing valid responses, and only AFTER validation does `res.lower()[0]` truncate (so "do"→y works via "yes", "al"→a); record a permanent in-process dismissal on `d`; wrap inner prompts with `restore_multiline` so a confirm mid-composition forces single-line and restores it in finally.
**Invariant:** group confirmations present the decision once per set; `explicit_yes_required` overrides blanket yes, hides the `(A)ll` OPTION (:834-835), and blocks its promotion (`is_yes = res == "y"` :908-909 instead of `res in ("y","a")` :911) — answering All IS a yes for the current item when allowed; is_all/is_skip require a live group (:913-914); `never_prompts` keys on `(question, subject)` so a file dismissal never silences another; dismissal persistence is IN-PROCESS ONLY (a plain set, never written to disk); multiline subjects render box-aligned (ljust to max line width, bold, :850-855).

### Response-resolution quirks (restored pass 11)
- **offer_url dead fast-path:** `offer_url(:797-804)` checks `url in self.never_prompts`, but that set holds `(question, subject)` TUPLES — a bare string can never match, so the guard is unreachable. Real suppression happens inside confirm_ask because its caller passes `question_id=(prompt, url)`. Behaviorally harmless (one wasted scan), but a porter must key consistently.
- **Truncation-after-validation ordering:** validating on full prefixes then truncating means single-letter answers and multi-letter unambiguous prefixes coexist ("n"/"no"/"nope" all → n). Validating after truncation would break the ladder.
- **Group replay echo:** preference replay calls `user_input(f"{question}{res}", log_only=False)` — display AND history write, keeping transcripts honest about batch decisions.
**Probe:** `.venv/bin/python -m pytest tests/basic/test_io.py -k 'confirm_ask' -q` within the executed subset (**7 passed**: test_confirm_ask_explicit_yes_required :177-206 assertNotIn "(A)ll", test_confirm_ask_with_group :209-248 mock_input.assert_not_called() after preference="all", test_confirm_ask_yes_no :251-301, test_confirm_ask_allow_never :304-342), plus `test_multiline_mode_restored_after_interrupt`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "confirm_ask ConfirmGroup never_prompts restore_multiline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-preference confirmation object and the `(question, subject)` never-set as the safe consent model: ask once, remember the group decision, key dismissals by (question, subject), and make destructive paths explicit-yes. Adapt rendering to the host; omit Aider's exact prompt strings.
