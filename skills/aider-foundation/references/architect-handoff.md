<!-- capsule-v2 -->
# Plan-to-edit handoff — isolate the edit pass behind a consent gate

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How can a harness turn an architectural response into edits without letting planning-state or an unreviewed plan mutate files directly?

## Plan-to-edit transfer
**Path/Symbol:** `aider/coders/architect_coder.py`: `ArchitectCoder.reply_completed()` (:11-48).
**Signature:** `reply_completed(self) -> None`.
**Data Shape:** architect `partial_response_content`; `auto_accept_architect`; main/editor model pair; a fresh editor coder that inherits only explicit state and receives the plan as a new message with cleared histories.

### Decisive source
```python
if not self.auto_accept_architect and not self.io.confirm_ask("Edit the files?"):
    return
editor_model = self.main_model.editor_model or self.main_model
new_kwargs = dict(io=self.io, from_coder=self)
new_kwargs.update(main_model=editor_model, edit_format=self.main_model.editor_edit_format,
                  suggest_shell_commands=False, map_tokens=0, cache_prompts=False,
                  summarize_from_coder=False)
editor_coder = Coder.create(**new_kwargs)
editor_coder.cur_messages = []
editor_coder.done_messages = []
editor_coder.run(with_message=content, preproc=False)
```

**Flow:** discard an empty plan; require consent unless auto-accept was explicitly enabled; select the dedicated editor model/format; create a fresh editor coder; clear conversational histories so the plan is the sole work message; run it with prior-user-proc disabled; copy cost and commit outcomes back to the architect session.

**Invariant:** a normal architect response cannot edit until the user consents. The edit session has a blank transcript and no repo map/cache warming, so planning dialogue cannot leak into edit-format instructions.

**Probe:** `tests/basic/test_coder.py::test_architect_coder_auto_accept_true`, `test_architect_coder_auto_accept_false_confirmed`, and `test_architect_coder_auto_accept_false_rejected` (:1330-1434) assert the acceptance boundary and that rejection never creates or runs the editor.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "ArchitectCoder reply_completed editor_coder confirm_ask", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a consent-gated, fresh-session plan-to-edit handoff; adapt model and session construction; omit Aider-specific prompt wording and cost fields.
