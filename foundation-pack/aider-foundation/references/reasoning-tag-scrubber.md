<!-- capsule-v2 -->
# Reasoning-tag scrubber — DOTALL pair removal plus closing-tag salvage for truncated streams

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you strip model chain-of-thought from a response that may arrive complete, or truncated mid-reasoning by a stream cut?

## Two-pass removal: full pairs first, then "everything before the closing tag"
**Path/Symbol:** `aider/reasoning_tags.py`: `REASONING_TAG` constant (:8, `"thinking-content-" + "7bbeb8e1441453ad999a0bbba8a46d4b"` split-string form), `remove_reasoning_content(res, reasoning_tag)` (:14), `replace_reasoning_tags(text, tag_name)` (:43), `format_reasoning_content(reasoning_content, tag_name)` (:67).
**Signature:** removal is regex `<tag>.*?</tag>` with `re.DOTALL`, `.strip()`; then if `</tag>` still present, keep everything AFTER the FIRST closing tag only.
**Data Shape:** display constants `REASONING_START = "--------------\n► **THINKING**"` / `REASONING_END = "------------\n► **ANSWER**"` (note the deliberately different dash counts); `replace_reasoning_tags` rewrites arbitrary `<tagname>…</tagname>` into that display format with normalized blank-line spacing; consumed by base_coder at :1890/:1962/:1980 (`show_resp = replace_reasoning_tags(...)`).

### Decisive source
```python
pattern = f"<{reasoning_tag}>.*?</{reasoning_tag}>"
res = re.sub(pattern, "", res, flags=re.DOTALL).strip()
# If closing tag exists but opening tag might be missing, remove everything
# before closing tag
closing_tag = f"</{reasoning_tag}>"
if closing_tag in res:
    parts = res.split(closing_tag, 1)
    res = parts[1].strip() if len(parts) > 1 else res
```

**Flow:** base_coder calls the scrubber on `partial_response_content` before treating it as the answer; the formatter wraps raw `reasoning_content` fields from providers into tagged text so the same pipeline handles both wire shapes. EXECUTED BEHAVIOR PROBE this run: full pair `<t>secret thinking</t>answer here` → `'answer here'`; orphan closing tag `orphan </t> visible answer` → `'visible answer'` — both green against live source.
**Invariant:** an unclosed tag at stream-truncation still yields pure answer content IF any closing tag exists later; a response with NO closing tag keeps everything (fail-open toward showing content rather than eating the answer).
**Probe:** deterministic: `grep -c 'closing_tag' aider/reasoning_tags.py` → 3. Direct tests: `tests/basic/test_reasoning.py::test_send_with_reasoning_content` (:16) + `::test_remove_reasoning_content` (:367) executed GREEN this run via repo venv (`python -m pytest tests/basic/test_reasoning.py -q`: **8 passed**; asserts REASONING_START/END ordering and `partial_response_content == main_content`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "remove_reasoning_content", limit: 3 });
// rank-1: aider.aider.reasoning_tags.remove_reasoning_content aider/reasoning_tags.py 14-40
```

## Verdict
Adopt the two-pass scrub verbatim for any tag-delimited hidden-channel protocol; adapt the display markers. The closing-tag salvage arm is the non-obvious half porters omit — without it every truncated stream leaks reasoning into the visible answer.
