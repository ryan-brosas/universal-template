<!-- capsule-v2 -->
# diff-parse-timeout-first-wins — How is untrusted LLM diff text parsed safely, and what wins on duplicates?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** Which regex engine, what timeout semantics, and which duplicate/dedup rules govern diff parsing?

## Safe diff parsing seam
**Path/Symbol:** `gpt_engineer/core/chat_to_files.py:parse_diffs` (:123-161), `parse_diff_block` (:164-218), `parse_hunk_header` (:221-245).
**Signature:** `parse_diffs(diff_string: str, diff_timeout=3) -> dict`; uses `from regex import regex` — the THIRD-PARTY regex module, NOT stdlib re.
**Data Shape:** dict{filename_post: Diff}; block grammar: fenced ``` containing `--- pre\n+++ post\n@@ a,b @@\n([-+ ].*\n)*`.

### Decisive source
```python
from regex import regex                     # third-party! supports timeout=
diff_block_pattern = regex.compile(
    r"```.*?\n\s*?--- .*?\n\s*?\+\+\+ .*?\n(?:@@ .*? @@\n(?:[-+ ].*?\n)*?)*?```",
    re.DOTALL,
)
try:
    for block in diff_block_pattern.finditer(diff_string, timeout=diff_timeout):
        diff = parse_diff_block(block.group())
        for filename, diff_obj in diff.items():
            if filename not in diffs: diffs[filename] = diff_obj
            else: print(f"\nMultiple diffs found for {filename}. Only the first one is kept.")
except TimeoutError:
    print("gpt-engineer timed out while parsing git diff")
```
```python
pattern = re.compile(r"^@@ -\d{1,},\d{1,} \+\d{1,},\d{1,} @@$")
if not pattern.match(header_line):
    return 0, 0, 0, 0     # malformed header degrades to zeros, later repaired from counts
```

**Flow:** timeout-guarded global scan → per-block state machine: `--- ` sets pre-name, `+++ ` flushes prior hunk and opens a NEW Diff keyed by post-name, `@@ ` flushes prior hunk and starts next, +/-/space classify lines (RETAIN keeps `line[1:]` so blank retains become "") → final flush.
**Invariant:** (1) The `timeout=` kwarg EXISTS ONLY on the third-party regex module — porting to stdlib `re` silently loses ReDoS protection against adversarial model output; keep the dependency. (2) FIRST diff per filename wins; later duplicates are printed and dropped — combined with the preprompt RULE "single diff chunk per file" this makes overwrite ambiguity impossible. (3) Malformed hunk headers yield (0,0,0,0) which Diff.validate_and_correct later recomputes from actual category_counts — header lies are repaired downstream, not here. (4) Zero diffs parsed prints a user-guidance message and returns {} — callers treat empty as "no changes". (5) parse_diff_block strips first/last lines assuming a fence, so feeding unfenced text shifts classification by one line.
**Probe:** `grep -n 'from regex import regex' gpt_engineer/core/chat_to_files.py` → :29 (module identity pin).
**Probe:** `grep -n 'timeout=diff_timeout' gpt_engineer/core/chat_to_files.py` → :141 (timeout actually wired).
**Probe:** `tests/core/test_chat_to_files.py::test_multi_diff_discard` pins duplicate-drop; `test_diff_regex` pins block splitting (1 then 2 diffs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "parse_diffs diff_block_pattern timeout parse_hunk_header", limit: 10 });
```

## Verdict
Adopt third-party-regex timeout parsing and first-wins dedupe verbatim (security + determinism); adapt block grammar if your fence conventions differ; omit stdlib-re "simplification" — it removes the DoS bound.
