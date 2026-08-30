<!-- capsule-v2 -->
# Skill discovery & load_skill tool — how do you turn SKILL.md frontmatter into agent-callable instructions WITHOUT letting a hostile SKILL.md inject prompt/template syntax?

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where is the trust boundary for third-party skill files — what gets sanitized, what gets rejected, and why does the load_skill tool PRINT its own return value?

## Sanitized parse + print-through loader
**Path/Symbol:** `src/cuga/backend/skills/loader.py` (`_JINJA_RE` :23; `_sanitize_for_prompt` :26-34; `_parse_skill_file` :139-166; `discover_skills` :169-197; `get_skill_root` :59-91), `registry.py` (`SkillEntry` :16-23; `SkillRegistry.load_skill` :39-64), `tools.py` (`create_skill_tools` :20-42).
**Signature:** `discover_skills(cuga_folder, *, root=None) -> List[SkillEntry]`; `load_skill(name: str, args: str = "") -> str`; `create_skill_tools(registry) -> list[StructuredTool]`.
**Data Shape:** SkillEntry(frozen): name/description/body/source + requirements tuple (pip items bare, npm prefixed `npm:`; dict forms normalize pip/pip_packages/python/python_packages and npm/npm_packages/node/node_packages keys) + arguments tuple (whitespace string or YAML list). Single-root discovery: exactly ONE of `<cuga>/skills`, `<cuga-folder>/.agents/skills`, or global roots per `settings.skills.root` preset.

### Decisive source
```python
# loader.py:21-34 — Jinja2 delimiters in frontmatter are PROMPT INJECTION
# because the system-prompt template renders them; strip at PARSE time
_JINJA_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)
sanitized = _JINJA_RE.sub("", value)
if sanitized != value:
    logger.warning(f"Skill {source}: {field!r} contained Jinja2 template syntax...")

# loader.py:147-149 — name must be filesystem-safe BEFORE it's used as a dir
name_str = _sanitize_for_prompt(str(name).strip(), "name", path)
if re.search(r'[/\\]|\.\.', name_str):
    raise ValueError(f"unsafe skill name {name_str!r}: ...")   # file skipped (except → None)

# registry.py:52-63 — loaded output = guidance + companions + playbook +
# command-normalization preamble, THEN the body as STEP 1 (never STEP 2)
skill_dir = f"/workspace/skills/{entry.name}"
parts = [LOAD_SKILL_GUIDANCE, "", LOAD_SKILL_COMPANIONS.format(skill_dir=skill_dir),
         "", LOAD_SKILL_PLAYBOOK, "", LOAD_SKILL_COMMAND_NORMALIZATION,
         "", f"STEP 1 — SKILL INSTRUCTIONS:\n{body}"]

# tools.py:26-29 — the stdout capture of the code-agent is the ONLY guaranteed
# delivery channel into the model's context:
print(instructions)   # even if the generated code discards the return value
return instructions
```

**Flow:** rglob("SKILL.md") sorted → per-file isolation (any parse error logs + skips that file only) → sanitize name+description → reject traversal names → validate arg names against slash-command substitution rules (numeric-only names collide with `$N` positional syntax → whole skill dropped) → first-discovery-wins per name within the single root. Load: exact name match else "Unknown skill" listing known names → optional `$ARGUMENTS`/`$name`/`$N` substitution when args supplied (verbatim body without args) → wrap in fixed guidance frame.
**Invariant:** (1) Sanitization happens at PARSE time on name/description only — body is NOT sanitized (it's delivered as data via the tool result, never rendered through the system-prompt template); moving skills into template rendering would re-open the injection hole. (2) Invalid files are skipped SILENTLY-ish (warning log), never fatal to discovery. (3) The unconditional `print` is load-bearing: an agent writing `await load_skill(...); print("ok")` would otherwise never see the instructions and improvise. (4) Companion-file references route through `{skill_dir}` = `/workspace/skills/<name>` — the sandbox copy path must place files there or companions 404.
**Probe:** `tests/unit/test_skill_loader.py` — `test_discover_skills_uses_single_root_only` (:53 four roots planted, ONE returned), `test_skill_name_with_path_traversal_is_rejected` (:242 returns None), `test_jinja_expression_in_description_is_stripped` (:262), `test_jinja_block_in_description_is_stripped` (:281 asserts both delimiters gone), `test_jinja_expression_in_name_is_stripped` (:300), `test_loader_rejects_skill_with_numeric_argument_name` (:349 skill dropped), `test_load_skill_tool_prints_instructions_even_if_agent_discards_return` (:146 capsys pins the print side-effect), `test_load_skill_substitutes_args_into_body` (:364).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "discover_skills _sanitize_for_prompt _parse_skill_file SkillRegistry load_skill create_skill_tools", limit: 10 });
```

## Verdict
Adopt parse-time Jinja2 stripping of frontmatter, traversal-name rejection with skip-not-fatal isolation, single-root precedence, the fixed guidance-frame wrapper ending in "STEP 1 — SKILL INSTRUCTIONS", and the print-through tool contract. Adapt root presets and the `/workspace/skills` virtual dir to your host's sandbox layout. Omit nothing from the sanitization pair — stripping delimiters but keeping their payload is the tested behavior ("malicious_var" must not survive).
