<!-- capsule-v2 -->
# SKILL.md format layer — how do spec-compliant skills load, validate, and round-trip without forking the agentskills.io standard?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter wanting drop-in compatibility with the existing skill ecosystem (anthropics/skills, openai/skills) must know where spec fields end and lifecycle extensions begin, which validator rules are hard vs soft, and what the parse/serialize round-trip must preserve.

## SkillMetadata — spec fields + namespaced extension
**Path/Symbol:** `modules/providers/skills/base.py:SkillMetadata` (46-164), `AGENT_LOOP_NAMESPACE = "agent-loop"` (29), `from_raw` (82-115) / `to_frontmatter_dict` (117-164); enums SkillStatus/SkillSource (32-43); shared structural filter `matches_filter` (253-274).
**Signature:** `SkillMetadata.from_raw(data: dict) -> SkillMetadata`; `to_frontmatter_dict() -> dict`.
**Data Shape:** Spec fields: name, description, license, compatibility, metadata, allowed_tools (parsed from space-separated `allowed-tools`). Extension fields (version/category/subcategory/tags/status/source/timestamps/deprecated_reason/replaced_by/related/requires/concepts/pack_name/pack_version) live ONLY inside `metadata["agent-loop"]` on disk. Defaults everywhere — a third-party SKILL.md with NO namespace loads fine.

### Decisive source
```python
# base.py — the round-trip that keeps third-party metadata intact
ext = dict(raw_metadata.get(AGENT_LOOP_NAMESPACE) or {})
allowed_tools = allowed_tools_raw.split() if isinstance(allowed_tools_raw, str) else None
...
merged_metadata = dict(self.metadata)          # human/third-party keys preserved untouched
merged_metadata[AGENT_LOOP_NAMESPACE] = ext    # our namespace re-nested on write
data["metadata"] = merged_metadata
```

**Flow:** YAML frontmatter dict → from_raw lifts namespaced fields with defaults → in-memory Skill carries them as first-class pydantic fields → to_frontmatter_dict re-nests under `agent-loop` → yaml.safe_dump → valid spec SKILL.md any other parser accepts.
**Invariant:** The extension is an OVERLAY, never a fork: unknown-hostile parsers see ignorable ordinary metadata; every extended field defaults so foreign files load; foreign top-level metadata keys survive a full read-modify-write cycle.
**Probe:** `tests/unit/agent_loop_lib/modules/providers/skills/test_manager.py::TestCandidateToSkillMd::test_renders_valid_frontmatter_with_agent_created_source` (pins agent-created provenance rendering through to_frontmatter_dict).

## loader.py / validator.py — parse + enforce split
**Path/Symbol:** `loader.py:parse_skill_md` (46-73), `render_skill_md` (76-84), `iter_skill_dirs`/`_walk_for_skills` (106-136), `load_skill_file` (139-167), `load_skills_from_dir` (170-183); `validator.py:SkillValidator` (56-165) with limits MAX_NAME 64 / MAX_DESCRIPTION 1024 / MAX_BODY 200_000 (23-26).
**Signature:** `parse_skill_md(content, *, expected_name=None, validator=None) -> Skill`; `iter_skill_dirs(root, max_category_depth=2)` yields `(skill_dir, category, subcategory)`.
**Data Shape:** Skill = metadata + body + root_dir + precomputed `resources: {kind: [relpaths]}` (scripts/references/assets enumerated, NEVER read). Category inferred from directory position (`cat/subcat/name/SKILL.md`) but explicit frontmatter ALWAYS wins over the directory hint.

### Decisive source
```python
# loader.py — one broken file must not take down a scan; _/. dirs are never skills
except (SkillFormatError, OSError) as e:
    logger.warning("Skipping invalid skill at %s: %s", skill_path, e)
...
if entry.startswith(_IGNORED_PREFIXES):        # ('_', '.') protects _meta/, .git/
    continue
...
elif depth < max_depth:
    next_category = category if category is not None else entry      # first level = category
    next_subcategory = entry if category is not None else None       # second = subcategory
```

**Flow:** walk roots up to 2 category levels → dir-with-SKILL.md yields (dir, category, subcategory) → parse (regex-split frontmatter, safe_load, validate name+description, enforce name==dirname when layout implies it) → attach root_dir + resource listing. Write path: create/update re-parse + full validate BEFORE disk; patch validates the patched body; render_skill_md is THE shared serializer.
**Invariant:** Validation lives in ONE stateless class shared by reader and writer ("is this a valid skill" can't drift between paths). Hard limits block saves unconditionally; `lint()` warnings (body >500 lines, ~>5000 tokens, description-reads-like-a-workflow hints, nested references >1 deep) never do — lint supplements, never replaces. Malformed files are skipped-with-log, not fatal. `_`/`.`-prefixed dirs are invisible to scans (protects manager-owned `_meta/`).
**Probe:** `tests/unit/agent_loop_lib/modules/providers/skills/test_filesystem_store.py::TestCreateSkill/TestUpdateSkill/TestPatchSkill` (pins validation-before-disk, name==dirname enforcement, patch single-match semantics); `test_manager.py::TestLifecycle`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "parse_skill_md iter_skill_dirs", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SkillValidator validate_skill lint", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SkillMetadata from_raw to_frontmatter_dict", limit: 10 });
```

## Verdict
Adopt the namespaced-metadata overlay (spec-compat day-one interop with the agentskills.io ecosystem), the single shared validator with hard-vs-lint split, directory-inferred categories that explicit frontmatter overrides, skip-not-fail scanning, and `_`/`.` prefix hygiene. Adapt length limits and lint thresholds to host conventions. Omit nothing in this seam — it is the portability core of the subsystem.
