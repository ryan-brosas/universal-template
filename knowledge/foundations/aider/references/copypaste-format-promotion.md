<!-- capsule-v2 -->
# Copy-paste edit-format promotion — auto_select_context flips model format to its editor twin

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When the user runs with clipboard watching (`--copy-paste`), why does the effective edit format silently change, and under what rule?

## If the user didn't pin --edit-format, any of diff/whole/diff-fenced promotes to editor-<same>; anything else is left alone
**Path/Symbol:** `aider/main.py` :871-873; interacts with `ClipboardWatcher` spawn :1038-1040 and `--apply-clipboard-edits` branch :1095-1097 (which instead swaps to `main_model.editor_edit_format` and rewrites the message to `/paste`).
**Signature:**
```python
if args.copy_paste and args.edit_format is None:
    if main_model.edit_format in ("diff", "whole", "diff-fenced"):
        main_model.edit_format = "editor-" + main_model.edit_format
```
**Data Shape:** promoted values map onto registered coder classes (EditorEditBlockCoder `editor-diff`, EditorWholeFileCoder `editor-whole`, EditorDiffFencedCoder `editor-diff-fenced`) — all three exist in the coders registry, so the string concat is registry-safe by construction.

### Decisive source
```python
if args.copy_paste and args.edit_format is None:
    if main_model.edit_format in ("diff", "whole", "diff-fenced"):
        main_model.edit_format = "editor-" + main_model.edit_format
```

**Flow:** copy-paste mode means edits arrive as pasted diffs from an external chat window; aider therefore wants the EDITOR variants (no repo-context questions, no reflection loops — just apply) but only when the user expressed no format preference; explicit `--edit-format` always wins.
**Invariant:** promotion happens BEFORE Coder.create (:973) so analytics "cli session" records the FINAL format; models whose default isn't in the trio (e.g. architect, patch) are untouched because there is no editor twin to promote into.
**Probe:** deterministic anchors: `grep -nF 'editor-" + main_model.edit_format' aider/main.py` → exactly :873; `grep -nF 'apply_clipboard_edits' aider/main.py | head -2` → :1095/:1096. Direct tests: none upstream for this specific branch (source-pinned caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "copy_paste ClipboardWatcher", limit: 3 });
// resolves the promotion site + watcher wiring in main.py
```

## Verdict
Adopt the pattern when a runtime mode should upgrade an interaction format only in the ABSENCE of explicit user choice — the None-check is the whole ethic. Port this only alongside a real clipboard pipeline; otherwise omit the trigger and keep formats static.
