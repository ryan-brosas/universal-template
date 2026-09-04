<!-- capsule-v2 -->
# Skill Packaging Exclusions — how is a skill folder zipped into a distributable .skill, and what gets left out?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** What does the official packager exclude, why is one exclusion root-scoped, and what must happen before any zip byte is written?

## Validate-first packaging with a root-only evals carve-out
**Path/Symbol:** `skills/skill-creator/scripts/package_skill.py::should_exclude` (:27–39) + `package_skill` (:42–108, read whole).
**Signature:** `should_exclude(rel_path: Path) -> bool`; `package_skill(skill_path, output_dir=None) -> Path | None`.
**Data Shape:** exclusion sets: `EXCLUDE_DIRS = {"__pycache__","node_modules"}` (any depth), `EXCLUDE_GLOBS = {"*.pyc"}`, `EXCLUDE_FILES = {".DS_Store"}`, and `ROOT_EXCLUDE_DIRS = {"evals"}` — excluded ONLY at the first directory level under the skill root (:32–35 uses `parts[1]`, because rel_path is relative to `skill_path.parent`, so parts[0] is the skill folder itself).

### Decisive source
```python
# rel_path is relative to skill_path.parent, so parts[0] is the skill
# folder name and parts[1] (if present) is the first subdir.
if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
    return True
```
```python
print("🔍 Validating skill...")
valid, message = validate_skill(skill_path)
if not valid:
    print(f"❌ Validation failed: {message}")
    print("   Please fix the validation errors before packaging.")
    return None
```
(validate-before-package at :70–77 — an invalid skill can never produce a .skill artifact; arcname = `file_path.relative_to(skill_path.parent)` at :96 preserves the skill folder as the zip's single root entry.)

**Flow:** resolve path → existence + is-dir checks (each returning None with a ❌ message) → SKILL.md presence check → validate_skill gate → mkdir output dir (or cwd) → ZIP_DEFLATED walk of rglob('*'), skipping non-files and should_exclude hits with a printed `Skipped:` line → `{skill_name}.skill` written next-level-up.
**Invariant:** `evals/` ships separately ON PURPOSE — eval prompts and graded runs are development scaffolding, not runtime payload, but nested dirs named evals deeper inside resources DO ship. The porter who converts this to a blanket name filter silently strips legitimate nested content; the porter who drops the validate gate distributes broken skills. Zip root = the skill folder (arcnames start with it), so consumers unzip into a ready-made directory.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -cF 'ROOT_EXCLUDE_DIRS = {"evals"}' skills/skill-creator/scripts/package_skill.py` = 1; `grep -c 'parts\[1\] in ROOT_EXCLUDE_DIRS' skills/skill-creator/scripts/package_skill.py` = 1; behavioral (executed): package a fixture dir with an evals/ subdir and confirm `zipinfo` lists no evals/ entries but lists a nested `resources/evals/` if present.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "should_exclude package_skill", limit: 5 });
// skills.skills.skill-creator.scripts.package_skill.should_exclude Function package_skill.py 27-39
```

## Verdict
Adopt validate-before-package ordering, the four-tier exclusion taxonomy (dirs-any-depth / globs / files / root-only dirs), and folder-rooted zip layout for any skill/plugin bundler. Adapt the exclusion sets to your ecosystem's build artifacts. Omit the emoji CLI dressing.
