<!-- capsule-v2 -->
# Skill Validation Gate — which frontmatter keys and value grammars must a SKILL.md pass before it is distributable?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** What is the complete machine-checkable validity contract for a SKILL.md, and where does it intentionally stay silent?

## Closed-vocabulary frontmatter validation
**Path/Symbol:** `skills/skill-creator/scripts/quick_validate.py::validate_skill` (:12–94, read whole; graph-resolved line-exact).
**Signature:** `validate_skill(skill_path) -> tuple[bool, str]` — message doubles as CLI output; exit 0 iff valid.
**Data Shape:** `ALLOWED_PROPERTIES = {'name','description','license','allowed-tools','metadata','compatibility'}` — any other top-level key FAILS with the full allowed list in the error. Name grammar: `^[a-z0-9-]+$`, no leading/trailing hyphen, no `--`, ≤64 chars. Description: string, NO angle brackets (`<`/`>`) anywhere, ≤1024 chars. Compatibility: optional, ≤500 chars. Frontmatter must start byte-0 with `---` and close with a second `---`; YAML must parse to a dict via `yaml.safe_load`.

### Decisive source
```python
# Check for unexpected properties (excluding nested keys under metadata)
unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
if unexpected_keys:
    return False, (
        f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
        f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
    )
```
```python
# Check for angle brackets
if '<' in description or '>' in description:
    return False, "Description cannot contain angle brackets (< or >)"
```

**Flow:** file exists → content.startswith('---') → regex-extract frontmatter block → safe_load → dict check → closed-vocabulary key check → name checks (type → strip → grammar → hyphen edges → length) → description checks (type → strip → angle brackets → length) → compatibility length → `"Skill is valid!"`.
**Invariant:** The vocabulary is CLOSED — unknown keys are errors, not warnings, so typo'd or invented fields can't silently become load-bearing on some other host. Nested `metadata.*` sub-keys are explicitly exempt from the vocabulary check (:45 comment) — metadata is the sanctioned extension point. Angle brackets are banned because descriptions get injected into prompt contexts where they'd read as tags. Empty-string name/description pass the grammar checks but fail earlier on presence — the validator validates SHAPE, not semantic quality (that's what evals are for).
**Probe:** No upstream tests. Deterministic: `grep -c "ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}" skills/skill-creator/scripts/quick_validate.py` = 1 (re-derived & executed 2026-08-24; the set literal sits on its own line at :42); behavioral (executed): ran validate_skill against this repo's own foundation leaves — canonical leaf frontmatter (name+description only) passes, a fixture with an extra `triggers:` key fails with the sorted unexpected-key message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "validate_skill", limit: 5 });
// skills.skills.skill-creator.scripts.quick_validate.validate_skill Function quick_validate.py 12-94
```

## Verdict
Adopt the closed vocabulary + kebab-case grammar + 64/1024 limits as the portability contract for any skill-format you define; adopt the metadata escape hatch pattern instead of opening the vocabulary. Adapt limits if your loader's budget differs (keep them hard failures). Omit nothing — this is the reference implementation of skill-format linting.
