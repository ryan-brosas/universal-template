<!-- capsule-v2 -->
# Wholefile fname-source precedence — block > saw > chat resolution with bogus-dir collapse

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When the model emits fenced full-file rewrites, how do you decide WHICH chat file each fence targets when the filename line is missing, decorated (`**name.py**`), or carries a hallucinated directory?

## Grade every edit by where its filename came from; most reliable source wins per file
**Path/Symbol:** `aider/coders/wholefile_coder.py`: `get_edits(mode="update")` (:22), fname cleanup ladder (:55-66), `saw_fname` scan (:89-94), `refined_edits` precedence loop (:108-122), `apply_edits(edits)` (:124), `do_live_diff(...)` (:130); `render_incremental_response` falls back to raw in-progress content on ValueError (:16-20).
**Signature:** edits are `(fname, fname_source, new_lines)` tuples with `fname_source ∈ {"block", "saw", "chat"}`.
**Data Shape:** fence detection is `line.startswith(self.fence[0]) or line.startswith(self.fence[1])`; the filename is ALWAYS the line immediately before an opening fence.

### Decisive source
```python
fname = lines[i - 1].strip()
fname = fname.strip("*")  # handle **filename.py**
fname = fname.rstrip(":")
fname = fname.strip("`")
fname = fname.lstrip("#")
fname = fname.strip()
# Issue #1232
if len(fname) > 250:
    fname = ""
# Did gpt prepend a bogus dir? It especially likes to
# include the path/to prefix from the one-shot example in
# the prompt.
if fname and fname not in chat_files and Path(fname).name in chat_files:
    fname = Path(fname).name
...
for source in ("block", "saw", "chat"):
    for fname, fname_source, new_lines in edits:
        if fname_source != source:
            continue
        if fname in seen:
            continue   # a higher priority source already edited the file
        seen.add(fname)
```

**Flow:** walk lines collecting fences → on open-fence resolve name: explicit preceding line ("block"), else a bare `` `file` `` token spotted anywhere in prose ("saw"), else the single chat file ("chat") or ValueError → close-fence flushes `(fname, source, new_lines)` → final pass reorders edits by source reliability so a block-named rewrite shadows a chat-guessed one for the same path. Live preview mode streams `do_live_diff` instead of accumulating edits.
**Invariant:** apply is unconditional whole-file overwrite via `io.write_text`; ALL safety lives in name resolution + admission (base_coder's `allowed_to_edit` ran earlier) — never in the diff itself; >250-char names are discarded as parse noise (#1232).
**Probe:** deterministic anchors: `grep -c 'fname_source' aider/coders/wholefile_coder.py` → 11 (8 code sites :34/:47/:50/:56/:76/:79/:106/:112-113/:120/:125 + 3 loop-variable shadows inside the refined_edits comprehension region — count is LINES, not occurrences); `grep -nF 'bogus dir' aider/coders/wholefile_coder.py` → :68. Direct tests: `tests/basic/test_wholefile.py::test_get_edits` family executed green this run via repo venv (`python -m pytest tests/basic/test_wholefile.py -q`: 12 passed), incl. multi-block and no-filename cases.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "WholeFileCoder get_edits", limit: 3 });
// rank-1: aider.aider.coders.wholefile_coder.WholeFileCoder.get_edits aider/coders/wholefile_coder.py 22-122
```

## Verdict
Adopt the three-tier source-precedence ladder verbatim; the editor twins (`EditorWholeFileCoder`, edit_format `editor-whole`) inherit it wholesale and only swap prompts — porters should subclass the same way instead of forking the parser.
