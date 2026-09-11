<!-- capsule-v2 -->
# sys-prompt-sandwich — Why is the generation system prompt assembled from FOUR preprompt files?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What is the exact composition order of the codegen system prompt, and why does the FILE_FORMAT placeholder replacement matter?

## Preprompt composition seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:setup_sys_prompt` (:75-94) and `setup_sys_prompt_existing_code` (:97-118); preprompts live at `gpt_engineer/preprompts/`.
**Signature:** `setup_sys_prompt(preprompts: MutableMapping[Union[str, Path], str]) -> str`.
**Data Shape:** `preprompts` = filename→content mapping loaded wholesale by `PrepromptsHolder.get_preprompts()` (every file under the dir becomes a key). Keys used: `roadmap`, `generate`, `file_format`, `philosophy`, and for improve: `improve`, `file_format_diff`.

### Decisive source
```python
return (
    preprompts["roadmap"]                                              # "You will write a very long answer..."
    + preprompts["generate"].replace("FILE_FORMAT", preprompts["file_format"])
    + "\nUseful to know:\n"
    + preprompts["philosophy"]                                         # toolbelt prefs: pytest, dataclasses
)
```

**Flow:** roadmap (commitment to completeness) → generate instructions with FILE_FORMAT token substituted by the concrete file-shape spec → literal separator "\nUseful to know:\n" → philosophy (language/tooling preferences).
**Invariant:** (1) `FILE_FORMAT` is a TOKEN inside the `generate` (resp. `improve`) preprompt text — substitution happens at assembly time, so users who override preprompts must keep the token or lose the format spec entirely. (2) The improve variant swaps ONLY two ingredients: `improve` replaces `generate`, `file_format_diff` (unified-diff grammar with RULES like "ENSURE ALL CHANGES ARE PROVIDED IN A SINGLE DIFF CHUNK PER FILE") replaces `file_format`; roadmap/philosophy stay identical. (3) No trailing separators between roadmap and generate — concatenation is bare `+`.
**Probe:** `grep -n 'FILE_FORMAT' gpt_engineer/core/default/steps.py` → exactly 2 hits (:91 gen, :115 improve), proving the token-substitution sites.
**Probe:** `head -1 gpt_engineer/preprompts/roadmap` → "You will get instructions for code to write." (confirms roadmap is the leading block).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "setup_sys_prompt preprompts philosophy roadmap", limit: 10 });
```

## Verdict
Adopt the sandwich order and token-substitution mechanism for any prompt-template pack; adapt ingredient texts to your stack; omit the specific pytest/dataclasses opinions if porting to non-Python targets. Direct tests: `tests/core/default/test_steps.py` exercises both setup functions against real PREPROMPTS_PATH.
