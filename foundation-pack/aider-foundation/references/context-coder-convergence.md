<!-- capsule-v2 -->
# ContextCoder convergence loop — mention-set equality as the reflection exit condition

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you make the model itself pick which files to edit, using the same reflection machinery as code repair — and how do you decide when it has converged?

## A coder whose "edits" are chat-membership changes: done when mentioned files == added files
**Path/Symbol:** `aider/coders/context_coder.py`: `ContextCoder` (edit_format `"context"`), `__init__` map-budget swap (:11-19), `reply_completed()` (:21-50), `check_for_file_mentions` deliberately stubbed to `pass` (:52-53); prompts in `context_prompts.py`.
**Signature:** `__init__` mutates the repo_map: `self.repo_map.refresh = "always"`, `max_map_tokens *= map_mul_no_files` (:18), then zeroes `map_mul_no_files = 1.0` (:19) — pre-multiplying so every refresh is full-width.
**Data Shape:** sets compared: `current_rel_fnames` (files currently in chat) vs `mentioned_rel_fnames = get_file_mentions(content, ignore_current=True)`.

### Decisive source
```python
if mentioned_rel_fnames == current_rel_fnames:
    return True                      # converged: model listed exactly the chat files
if self.num_reflections >= self.max_reflections - 1:
    return True                      # give up quietly at the cap
self.abs_fnames = set()
for fname in mentioned_rel_fnames:
    self.add_rel_fname(fname)
self.reflected_message = self.gpt_prompts.try_again
```

**Flow:** each turn the model names files it believes need edits → aider adds ALL mentioned files to chat, clears per-file abs cache, and re-prompts with "try again" → loop exits on set-equality or reflection cap. Suppressing `check_for_file_mentions` prevents double-add side effects during ordinary turns.
**Invariant:** this coder never touches disk; its only output channel is chat membership. The budget swap guarantees the map always includes per-file tokens because file selection IS the task.
**Probe:** deterministic: `grep -nF 'map_mul_no_files' aider/coders/context_coder.py` → :18-19 exactly. NO direct upstream test file exists for ContextCoder (source-pinned caveat; test_coder.py covers base-class mention machinery it reuses).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "ContextCoder reflected_message", limit: 3 });
// rank-1: aider.aider.coders.context_coder.ContextCoder.__init__ aider/coders/context_coder.py 11-19
```

## Verdict
Adopt the pattern for any "planning/selection agent" built on an edit-loop substrate: reuse reflection, redefine the fixed point. Adapt the map-token multiplier; omit nothing else — the stubbed mention-checker is intentional architecture, not dead code.
