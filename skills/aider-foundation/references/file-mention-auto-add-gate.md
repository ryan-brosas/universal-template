<!-- capsule-v2 -->
# File-mention auto-add gate — adding files the model named, without false positives or nagging

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you detect repository files mentioned in free prose and auto-add them without matching plain words like "run" or re-asking after a refusal?

## Word-normalized match: full path wins; basenames only when separator-bearing AND unique AND new
**Path/Symbol:** `aider/coders/base_coder.py`: `get_file_mentions(content, ignore_current=False)` (:1714-1759), `check_for_file_mentions(content)` (:1761-1781).
**Signature:** `get_file_mentions -> set[rel_fname]`; `check_for_file_mentions -> str | None` (an "Added files: ..." reflection message).
**Data Shape:** candidate set = `get_addable_relative_files()` minus in-chat/read-only basenames; words normalized twice (sentence punctuation rstrip, quote/backtick/asterisk/underscore strip).

### Decisive source
```python
words = set(word.rstrip(",.!;:?") for word in content.split())
quotes = "\"'`*_"
words = set(word.strip(quotes) for word in words)
...
for rel_fname in addable_rel_fnames:
    normalized_rel_fname = rel_fname.replace("\\", "/")
    if normalized_rel_fname in normalized_words:
        mentioned_rel_fnames.add(rel_fname)          # full-path mention always wins
    fname = os.path.basename(rel_fname)
    # Don't add basenames that could be plain words like "run" or "make"
    if "/" in fname or "\\" in fname or "." in fname or "_" in fname or "-" in fname:
        fname_to_rel_fnames.setdefault(fname, []).append(rel_fname)
for fname, rel_fnames in fname_to_rel_fnames.items():
    if fname in existing_basenames: continue          # already in chat / read-only
    if len(rel_fnames) == 1 and fname in words:       # unique basename mention only
        mentioned_rel_fnames.add(rel_fnames[0])
...
group = ConfirmGroup(new_mentions)
for rel_fname in sorted(new_mentions):
    if self.io.confirm_ask("Add file to the chat?", subject=rel_fname, group=group, allow_never=True):
        self.add_rel_fname(rel_fname); added_fnames.append(rel_fname)
    else:
        self.ignore_mentions.add(rel_fname)           # refusal remembered all session
```

**Flow:** normalize words -> full normalized rel-path hit adds directly -> otherwise collect separator-bearing basenames -> keep only basenames unique among addable files and absent from existing chat/read-only basenames -> ask once per ConfirmGroup (allow_never) -> acceptances become chat files and produce the reflection text; refusals land in `ignore_mentions` permanently for the session.
**Invariant:** a plain word ("run", "make") can never trigger an add because candidate basenames must contain \/ . _ - ; ambiguous duplicates require the full path; a "no" answer is terminal for that session; read-only files are promotion-guarded upstream (see test :206).
**Probe:** `tests/basic/test_coder.py` — `test_check_for_file_mentions_read_only` (:206), `test_check_for_file_mentions_with_mocked_confirm` (:233), `test_get_file_mentions_various_formats` (:288), `test_get_file_mentions_multiline_backticks` (:369), `test_get_file_mentions_path_formats` (:408). Executed GREEN this run via repo `.venv`: 5 passed + 17 subtests. Anchors: `grep -nF 'ignore_mentions.add(rel_fname)' aider/coders/base_coder.py` -> :1778; `grep -nF 'word.strip(quotes)' ...` -> :1722.
**Coverage caveat:** none for cited ranges.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "check_for_file_mentions", limit: 4 });
// resolves base_coder + ContextCoder override + both direct tests
```

## Verdict
Adopt the three-condition basename rule (separator-bearing, unique, not-already-present) and the sticky refusal set as the admission grammar. Adapt the confirmation surface to host IO; omit Aider's exact punctuation strip list only if your tokenizer differs. ContextCoder overrides check_for_file_mentions to a no-op — selection agents must not re-enter the gate.