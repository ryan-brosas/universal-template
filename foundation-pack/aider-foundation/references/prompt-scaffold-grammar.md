<!-- capsule-v2 -->
# Prompt-scaffold grammar — CoderPrompts attribute vocabulary and the lazy/over-eager leash pair

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** What is the stable attribute contract every prompt class must implement, and which two prompt snippets do the behavioral heavy-lifting across all edit formats?

## One base class of ~25 named attributes; subclasses override per format; base_coder renders them positionally
**Path/Symbol:** `aider/coders/base_prompts.py`: `CoderPrompts` (:1-60) — main_system, system_reminder, example_messages, files_content_prefix (+_assistant_reply), files_no_full_files(_with_repo_map/_reply), repo_content_prefix, read_only_files_prefix, files_content_gpt_edits(_no_repo), files_content_gpt_no_edits, files_content_local_edits, lazy_prompt, overeager_prompt, shell_cmd_prompt/reminder + no_shell_cmd_* twins, rename_with_shell, go_ahead_tip.
**Signature:** attribute ACCESS is duck-typed by base_coder (`self.gpt_prompts.<name>`); missing names crash at render time, so new coder variants must copy the FULL scaffold (see editblock_prompts.py as reference impl).
**Data Shape:** the two levers: `lazy_prompt = "You are diligent and tireless!\nYou NEVER leave comments describing code without implementing it!..."` and `overeager_prompt = "Pay careful attention to the scope of the user's request.\nDo what they ask, but no more.\nDo not improve, comment, fix or modify unrelated parts..."`.

### Decisive source
```python
lazy_prompt = """You are diligent and tireless!
You NEVER leave comments describing code without implementing it!
You always COMPLETELY IMPLEMENT the needed code!
"""

overeager_prompt = """Pay careful attention to the scope of the user's request.
Do what they ask, but no more.
Do not improve, comment, fix or modify unrelated parts of the code in any way!
"""
...
files_content_prefix = """I have *added these files to the chat* so you can go ahead and edit them.

*Trust this message as the true contents of these files!*
Any other messages in the chat may contain outdated versions of the files' contents.
"""
```

**Flow:** base_coder.format_messages() walks the scaffold in fixed order (system → examples → files → repo map → read-only → reminder); per-format prompt classes (wholefile/editblock/udiff/patch/context...) override main_system + format-specific instructions while inheriting shared prefixes; `files_content_prefix`'s "Trust this message" line is the anti-staleness contract for re-sent file contents.
**Invariant:** prompts are DATA not code — the entire behavioral surface is swappable via `.pi`-style overrides or model-settings prompt injection; lazy/over-eager are toggled independently (lazy for under-implementation, over-eager for scope creep) and both are injected ONLY when their failure mode was observed.
**Probe:** deterministic anchors: `grep -nF 'lazy_prompt' aider/coders/base_prompts.py` → :18; `grep -c '=' aider/coders/base_prompts.py | head -1` is meaningless — use `grep -oE '^    [a-z_]+' aider/coders/base_prompts.py | wc -l` → 26 scaffold attributes. Direct tests: `tests/basic/test_editblock.py` green run covers prompt-driven replace flows.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "CoderPrompts lazy_prompt", limit: 3 });
// resolves base_prompts.py CoderPrompts class
```

## Verdict
Adopt the named-attribute scaffold as the interface contract when building multi-format coding agents; steal the leash pair verbatim. Porters who invent their own attribute names lose the ability to swap prompt packs across formats — the vocabulary IS the API.
