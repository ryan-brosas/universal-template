<!-- capsule-v2 -->
# Partial-diff live preview — last-common-line truncation with progress bar and fence-escape

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you render a streaming partial file rewrite as a sane diff, when the untouched tail of the original file would show as thousands of spurious deletions?

## Cut the original at the last line the new content actually matches; no overlap ⇒ empty output
**Path/Symbol:** `aider/diffs.py`: `diff_partial_update(lines_orig, lines_updated, final=False, fname=None)` (:43), `find_last_non_deleted(lines_orig, lines_updated)` (:105), `assert_newlines(lines)` (:36), `create_progress_bar(percentage)` (:26); consumers: `wholefile_coder.do_live_diff` and udiff live rendering.
**Signature:** `find_last_non_deleted` walks `difflib.ndiff` counting space-code (matched) lines; returns the 1-based count of original lines up to the LAST matched line, or `None` when NOTHING matches.
**Data Shape:** all inputs are keepends=True line lists (`assert_newlines` enforces every non-final line ends `\n`); output is a fenced ```` ```diff ```` block with fence length escalated 3→9 backticks until it doesn't collide with diff content.

### Decisive source
```python
if final:
    last_non_deleted = num_orig_lines
else:
    last_non_deleted = find_last_non_deleted(lines_orig, lines_updated)
if last_non_deleted is None:
    return ""            # zero overlap: show nothing rather than a wall of deletions
...
pct = last_non_deleted * 100 / num_orig_lines
bar = f" {last_non_deleted:3d} / {num_orig_lines:3d} lines [{bar}] {pct:3.0f}%\n"
lines_orig = lines_orig[:last_non_deleted]
if not final:
    lines_updated = lines_updated[:-1] + [bar]   # replace still-streaming last line
diff = difflib.unified_diff(lines_orig, lines_updated, n=5)
diff = list(diff)[2:]                            # drop ---/+++ headers
for i in range(3, 10):
    backticks = "`" * i
    if backticks not in diff:
        break
```

**Flow:** while streaming, the ORIGINAL is truncated to its last commonly-matched line so everything past the model's live write-head is invisible (no phantom deletions); the in-progress final updated line is swapped for a progress-bar line showing N/M lines + percent; at `final=True` the full original participates and no bar is appended. EXECUTED BEHAVIOR PROBE this run: `orig=['l1\n','l2\n','l3\n','l4\n'], upd=['L1\n']` → `''` — a rewrite whose first line matches nothing yields EMPTY output, proving the None-overlap guard fires before any diff is built; only once streamed content shares a line with the original does the fenced diff+bar render.
**Invariant:** progress percent measures how far through the ORIGINAL file the rewrite has proven itself — not bytes streamed; the fence-escape loop guarantees the rendered block can be pasted back into chat without terminating early.
**Probe:** NO direct upstream test file for diffs.py (covered transitively via wholefile live-diff tests). Deterministic anchors: `grep -c 'last_non_deleted' aider/diffs.py` → 11; `grep -nF 'backticks' aider/diffs.py | head -1` → :87; behavior probe recorded above.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "find_last_non_deleted", limit: 3 });
// rank-1: aider.aider.diffs.find_last_non_deleted aider/diffs.py 105-124
```

## Verdict
Adopt verbatim for streaming whole-file previews; adapt n=5 context width and bar format to taste. The None-overlap empty return is load-bearing: without it ndiff on unrelated content produces a wall of full-file deletion noise on every tick.
