<!-- capsule-v2 -->
# LLM content-type salvage — how does a summary survive when the model returns a block list instead of a string?

**Source:** mem0 MIT `main@8d5b7865` (drift commit ed38ddf "huggingface TEI auth, procedural-memory content handling"); Codebase Memory `mem0`. **Question:** what input shapes must `remove_code_blocks` tolerate, and which empty-response case must STILL raise?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/utils.py` `remove_code_blocks` (:115-129); callers: `_create_procedural_memory` sync (:2011) + async (:3710), and the NEW empty guard (:2020-2024 / :3715-3719). Direct tests `tests/memory/test_memory_utils.py::TestRemoveCodeBlocks` (:193-211).
**Signature:** `remove_code_blocks(content) -> str`; accepts `None | str | list[str|dict]`.
**Data Shape:** list entries: bare strings joined verbatim; dicts contribute ONLY `block["text"]` (a `{"type": "thinking", "thinking": ...}` block contributes ""); anything else (e.g. int) → ""; fence regex `^```[lang]?\n(...)\n```$` applied to the stripped whole.
**Drift note:** pass-2 pin `001c2352` handled `None → ""` and strings only; `8d5b7865` adds the list branch + `isinstance(content, str)` final check.

### Decisive source
```python
if isinstance(content, list):                     # LangChain AIMessage .content can be a BLOCK LIST
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            parts.append(block.get("text", ""))   # thinking/other blocks degrade to ""
    content = "".join(parts)
if not isinstance(content, str):
    return ""                                     # None/int/anything non-text → empty
pattern = r"^```[a-zA-Z0-9]*\n([\s\S]*?)\n```$"
match = re.match(pattern, content.strip())        # ONE fenced whole only — inner fences survive
```
```python
# _create_procedural_memory — AFTER salvage, emptiness is still fatal:
procedural_memory = remove_code_blocks(procedural_memory)
...
if not procedural_memory:
    raise ValueError(
        "The LLM returned no content for the procedural memory summary. "
        "The model may have declined the request or returned an empty response.")
```

**Flow:** LLM response arrives as plain string OR provider-native block list → list form is flattened text-only (reasoning blocks dropped by key choice, not by type whitelist) → code-fence stripping runs on the joined string → the procedural-memory caller treats EMPTY-after-salvage as a loud ValueError while transport errors raise from the except block with context logged.
**Invariant:** salvage and refusal are COMPLEMENTARY, not contradictory — shape problems are normalized silently, but semantic emptiness (model declined/refused) must fail because storing "" as a procedural memory would corrupt the store; the fence regex anchors to the WHOLE stripped string so ```` ```json … ``` ```` unwraps exactly once; ordering matters: flatten BEFORE strip, strip BEFORE the empty check.
**Probe:** `tests/memory/test_memory_utils.py::test_list_content_from_langchain_aimessage_is_joined`, `::test_list_content_joins_multiple_blocks_and_bare_strings` (mixed blocks incl. thinking ignored), `::test_list_content_still_strips_code_fences`, `::test_unsupported_content_type_returns_empty_string`, `::test_none_content_returns_empty_string`. The new empty-guard itself has no direct test at this HEAD — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "remove_code_blocks procedural memory empty ValueError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flatten-then-strip-then-refuse ladder for any LLM-summary surface; adapt the block-dict text keys per provider; omit nothing — the empty raise is the load-bearing half.
