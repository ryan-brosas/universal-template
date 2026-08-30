<!-- capsule-v2 -->
# Collaboration loop — watch-mode AI comments + bounded reflection

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a harness let a human drive the model from their own editor and terminate self-correction loops instead of spinning forever?

## Watch-mode comments and capped reflection
**Path/Symbol:** `aider/watch.py`: `FileWatcher.get_ai_comments(filepath)` (:257), `ai_comment_pattern` (:69), `FileWatcher.handle_changes` dispatch (:185-215); `aider/coders/base_coder.py`: `Coder.run_one(user_message, preproc)` (:924), `max_reflections = 3` (:101).
**Signature:** `get_ai_comments(filepath) -> (line_nums, comments, has_action)`; `run_one(user_message, preproc) -> None`.
**Data Shape:** `has_action` is `None` (just add), `"!"` (change), or `"?"` (question); `run_one` drives a `while message:` loop where a set `self.reflected_message` becomes the next user message.

### Decisive source
```python
ai_comment_pattern = re.compile(r"(?:#|//|--|;+) *(?:ai\b.*|.*\bai[?!]?) *$", re.IGNORECASE)
# the cap is checked before re-entering the loop, so it can never exceed max_reflections turns
while message:
    self.reflected_message = None
    list(self.send_message(message))
    if not self.reflected_message:
        break
    if self.num_reflections >= self.max_reflections:
        self.io.tool_warning(f"Only {self.max_reflections} reflections allowed, stopping.")
        return
    self.num_reflections += 1
    message = self.reflected_message
```

**Flow:** `run_one` sends, reads `reflected_message`, reruns until None or the cap; a `FileWatcher` watches the workspace and on a changed AI-comment file adds it to chat and pauses input; `!`→`watch_code_prompt`, `?`→`watch_ask_prompt`, bare `ai` only auto-adds; applied edits auto-lint and failures become `reflected_message` until the cap.
**Invariant:** the reflection loop never exceeds `max_reflections`; the watcher passes comment text verbatim, never a paraphrase; only suffix-classified (`ai!`, `ai?`) dispatch action, bare `ai` just adds.
**Probe:** `tests/basic/test_watch.py::test_ai_comment_pattern` (:115) runs fixtures `watch.py/js/question.js/lisp` asserting exact comment counts and action classification; `test_gitignore_patterns` (:18), `test_handle_changes` (:99).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "get_ai_comments run_one reflected_message watch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt watch-mode as primary I/O and the capped reflection loop as the safety valve; port verbatim-comment fidelity and the per-interaction counter. Adapt the filesystem watcher and prompts to the host; omit Aider-specific comment syntax.
