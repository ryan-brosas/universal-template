<!-- capsule-v2 -->
# Flexible strategy engine — exact replace, then git cherry-pick 3-way merge, then line-granularity DMP

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** When a model's search text no longer byte-matches the file (drifted indentation, edited surroundings), how do you still land the intended change without corrupting anything?

## Strategy × preproc ladder
**Path/Symbol:** `aider/coders/search_replace.py`: `flexible_search_and_replace(texts, strategies)` (:565), `try_strategy(texts, strategy, preproc)` (:586), strategy trio (`search_and_replace` :434, `git_cherry_pick_osr_onto_o` :448, `dmp_lines_apply` :338), preproc tables `all_preprocs` (:528), `editblock_strategies` (:547), `strip_blank_lines` (:611), `relative_indent(texts)` (:239).
**Signature:** texts is the `(search_text, replace_text, original_text)` triple; `try_strategy -> str | None`; a falsy result means "this rung failed", never "apply partially".
**Data Shape:** strategies = ordered [(fn, [preproc tuples])] where preproc = `(strip_blank_lines: bool, relative_indent: bool, reverse_lines: bool)`; the reverse axis is commented out of `all_preprocs` — dead by design.

### Decisive source
```python
def flexible_search_and_replace(texts, strategies):
    # most literal interpretation first; progress to flexible only as needed
    for strategy, preprocs in strategies:
        for preproc in preprocs:
            res = try_strategy(texts, strategy, preproc)
            if res:
                return res

def try_strategy(texts, strategy, preproc):
    preproc_strip_blank_lines, preproc_relative_indent, preproc_reverse = preproc
    ri = None
    if preproc_strip_blank_lines:
        texts = strip_blank_lines(texts)
    if preproc_relative_indent:
        ri, texts = relative_indent(texts)   # all three texts share ONE RelativeIndenter
    ...
    if res and preproc_relative_indent:
        try:
            res = ri.make_absolute(res)      # inverse transform on the RESULT ONLY
        except ValueError:
            return                            # marker leaked = rung fails loudly
```

**Flow:** rung 1 exact `str.replace` under each preproc; rung 2 commits O→S→R in a throwaway Git repo and `cherry-pick --minimal` R onto O, treating `GitError/ODBError` (merge conflict) as rung failure; rung 3 diffs S→R at LINE granularity via `diff_linesToChars` + patch_apply with tight match knobs (`Match_Threshold=0.1, Match_Distance=100_000, Patch_Margin=1`) so a patch must anchor to near-exact lines.
**Invariant:** every rung is all-or-nothing (`patch_apply` success array checked with `False not in success` → else return None); the ladder degrades in CONTROLLED directions only (exact → semantic 3-way → line-DMP), never to character-fuzzy guessing; GitVendored cherry-pick uses a temp dir per call (`GitTemporaryDirectory`), no global state.
**Probe:** no upstream suite for this module → executed: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::flex-mangled-rescue` (deep-indent drift rescued through the preproc ladder, surrounding lines preserved) and `::flex-exact-replace` (absent search ⇒ None), repo venv GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "flexible_search_and_replace", limit: 5 });
// also resolves: dmp_lines_apply, git_cherry_pick_osr_onto_o, try_strategy (same file)
```

## Verdict
Adopt the ordered strategy×preproc ladder and its all-or-nothing contract wholesale — it is THE mechanism that makes LLM-authored edits robust; adapt which rungs you include and their DMP constants; omit the commented-out reverse-lines axis and the benchmarking `proc()/main()` harness (lines :622-757, offline eval tooling). Coverage caveat: graph-indexed, no direct tests upstream; probes executed this run are the behavioral pin.
