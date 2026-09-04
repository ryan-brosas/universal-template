<!-- capsule-v2 -->
# Frontmatter Parsing Without YAML — why does the optimizer re-parse SKILL.md by hand, and how do multiline descriptions survive?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** How does tooling extract name+description from a SKILL.md without a YAML dependency, and what multiline forms must it accept?

## Hand-rolled frontmatter scanner with multiline-indicator continuation
**Path/Symbol:** `skills/skill-creator/scripts/utils.py::parse_skill_md` (:7–47, whole file read; graph-resolved 7–47).
**Signature:** `parse_skill_md(skill_path: Path) -> tuple[str, str, str]` — returns `(name, description, full_content)`.
**Data Shape:** opening fence must be line 0 exactly (`lines[0].strip() != "---"` raises); closing fence = first line equal to `---` scanning from line 1. Values are matched by `startswith("name:")` / `startswith("description:")` prefix, then `.strip().strip('"').strip("'")`. Multiline indicators handled: `>`, `|`, `>-`, `|-` — any of these triggers a continuation loop that consumes following lines while they start with two spaces or a tab, strips each, and joins with single spaces.

### Decisive source
```python
elif line.startswith("description:"):
    value = line[len("description:"):].strip()
    # Handle YAML multiline indicators (>, |, >-, | -)
    if value in (">", "|", ">-", "|-"):
        continuation_lines: list[str] = []
        i += 1
        while i < len(frontmatter_lines) and (frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")):
            continuation_lines.append(frontmatter_lines[i].strip())
            i += 1
        description = " ".join(continuation_lines)
        continue
```

**Flow:** read whole file → fence-position scan → linear walk of frontmatter lines capturing name and description → return with FULL content so callers (improve_description) can re-embed the skill body into optimization prompts.
**Invariant:** This is a deliberate DEPENDENCY-FREE twin of quick_validate.py's yaml.safe_load path — scripts that only need name/description don't pay a PyYAML import. The continuation rule folds folded/literal scalars to one-line space-joined text, which is exactly what trigger-matching needs (whitespace-normalized). A porter who swaps in naive `key: value` splitting loses every multiline description — the common authoring style for long pushy descriptions per trigger-description-authoring.
**Probe:** No upstream tests. Deterministic: `grep -c '"|"' skills/skill-creator/scripts/utils.py` ≥ 1 (indicator tuple present; = 1 at this pin, re-derived & executed 2026-08-24); behavioral (executed): parse_skill_md on this leaf's own SKILL.md returns the full description string intact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "parse_skill_md", limit: 5 });
// skills.skills.skill-creator.scripts.utils.parse_skill_md Function utils.py 7-47
```

## Verdict
Adopt for any zero-dependency skill tooling: fence-scan + prefix-match + multiline-indicator continuation. Adapt quote-stripping order if your authors use quoted colons. Omit when PyYAML is already a hard dependency — then prefer safe_load but keep the same returned triple shape.
