<!-- capsule-v2 -->
# RelativeIndenter — indentation-relative text transform for drift-tolerant matching

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index 7,507n/19,923e). **Question:** How do you match two code blocks that encode the same edit but differ wholesale in their leading whitespace, without regex hacks?

## Pairwise delta-indent encoding
**Path/Symbol:** `aider/coders/search_replace.py`: `RelativeIndenter.__init__(texts)` (:83), `make_relative(text)` (:106), `make_absolute(text)` (:140), `select_unique_marker(chars)` (:98).
**Signature:** `__init__(texts: Iterable[str])` picks a sentinel char absent from ALL texts; `make_relative(text) -> str`; `make_absolute(text) -> str`.
**Data Shape:** each source line becomes TWO output lines: a delta-indent line (shared-prefix chars of this line's indent vs previous line's indent, or N× outdent-marker for negative deltas) followed by the indent-stripped content line. Blank lines keep zero indent and are NOT indented on rebuild (`if not non_indent.rstrip(...): out_line = non_indent`).

### Decisive source
```python
len_indent = len(line_without_end) - len(line_without_end.lstrip())
indent = line[:len_indent]
change = len_indent - len(prev_indent)
if change > 0:
    cur_indent = indent[-change:]      # only the NEW tail of the indent
elif change < 0:
    cur_indent = self.marker * -change # ← arrows count the outdent
else:
    cur_indent = ""
out_line = cur_indent + "\n" + line[len_indent:]
```
Rebuild inverts exactly: marker run shortens `prev_indent`, plain dent appends; `prev_indent = cur_indent` carries state across blank/content lines alike.

**Flow:** ctor scans every supplied text to choose a marker (`←` if unused, else first free codepoint scanning DOWN from U+10FFFF so private-use area is preferred); `make_relative` raises if the text already contains the marker; after strategy application `make_absolute` re-derives absolute indents and RAISES ValueError if any marker survived into the result (corrupt roundtrip).
**Invariant:** make_relative ∘ make_absolute is identity for marker-free input — both polarities verified live; the marker must never leak into output (raise, don't emit); uniform re-indentation of an entire block produces the SAME relative form (that's the whole point).
**Probe:** no dedicated upstream suite → executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::relindent-roundtrip` (identity roundtrip both polarities + ← marks outdents), repo venv GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "RelativeIndenter", limit: 5 });
// resolves: aider.aider.coders.search_replace (aider/coders/search_replace.py)
```

## Verdict
Adopt the delta-indent encoding + marker-hygiene contract verbatim (it is what makes whitespace-mangled LLM edits matchable); adapt the marker choice if your corpus already contains `←`; omit the dead `reverse_lines` preproc axis (commented out of `all_preprocs`). Coverage caveat: graph-indexed, no upstream direct tests — behavior pinned by the executed probe above.
