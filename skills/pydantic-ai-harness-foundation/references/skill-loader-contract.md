<!-- capsule-v2 -->
# Agent Skills loader: string-typed YAML, duplicate-key refusal, name-directory parity, acknowledged-not-active behavioral fields

## Source / Question
`pydantic_ai_harness/skills/_loader.py` — How do you load untrusted-ish SKILL.md packages so YAML's type coercion and duplicate-key semantics can't silently corrupt skill identity, and so clients that can't honor behavioral frontmatter don't pretend they did? Porters reach for default yaml.safe_load and inherit booleans-as-names bugs.

## Path / Symbol
`skills/_loader.py` — `_BEHAVIORAL_FRONTMATTER_FIELDS` frozenset (15–33: agent, allowed-tools, model, hooks, tools, …), `_SkillFrontmatter` BaseModel extra='allow' + non-empty description validator (38–51), `SkillDefinition` (54–60, carries `ignored_behavioral_fields`), `_extract_frontmatter` (63–80), `_parse_frontmatter` (82–126), `_normalize_name` (128–130, NFKC), `_discover_skills` (132–142, scandir sorted by entry name), `_validate_name` (145–161), `load_skill` (164–178), `load_skill_libraries` (181–236), `_validate_selection` (239–252).

## Signature
```python
class UniqueKeyLoader(yaml.BaseLoader):        # BaseLoader => ALL scalars stay strings
    def construct_mapping(self, node, deep=False):
        # reject duplicate scalar keys with ConstructorError naming the key
```

## Data Shape
SkillDefinition(name, description, body, ignored_behavioral_fields). Name rules: ≤64 lowercase Unicode alnum + single hyphens, no lead/trail hyphen, NFKC-normalized; must equal parent directory name when declared in frontmatter.

## Decisive source
1. **String-preserving YAML** (:89–93): "Agent Skills frontmatter fields are strings. BaseLoader preserves valid scalar names such as `123` and `on` instead of applying YAML implicit types" — a skill named `on` survives; PyYAML otherwise also accepts duplicate keys keeping the LAST value, which would silently rewrite identity, hence UniqueKeyLoader raises on duplicates (:94–110).
2. **Name-directory parity** (:171–174): a frontmatter name that doesn't normalize-match its directory is an error — discovery keys on directory names, so divergence would make include/exclude selectors lie.
3. **Behavioral fields acknowledged, not honored** (:14–33, :175–177): fields affecting invocation/permissions/model/execution in OTHER implementations are accepted for compatibility and REPORTED via `ignored_behavioral_fields` — "Skills accepts their files for compatibility but reports that the behavior is not active." Silent acceptance would feign enforcement.
4. **Fail-loud library hygiene** (:185–203): nonexistent library path, file-instead-of-directory (points AT a SKILL.md package), unknown include/exclude names (with full available list) all raise; duplicates across libraries raise naming both paths.
5. **Deterministic discovery**: scandir SORTED by name; include validates against discovered set before selection; exclude is difference-based.

## Flow / Invariant
validate libraries → discover child dirs w/ SKILL.md (sorted) → validate selection names → detect cross-library duplicate names → parse each file: extract delimited frontmatter (unclosed = error), unique-key string-typed YAML parse, model-validate (empty description rejected), name validation + parity check → SkillDefinition tuple. Invariants: loading is construction-time snapshot (later directory changes don't affect loaded defs); every rejection names the offending file and reason.

## Probe (direct test)
`tests/skills/test_skills.py`: `test_directory_name_is_used_when_frontmatter_omits_name` (:76), `test_selected_skills_are_deferred_capability_leaves` (:92), `test_loaded_instructions_contain_only_heading_and_body` (:118), `test_skill_directory_placeholder_is_not_resolved_to_a_host_path` (:150), `test_construction_is_a_snapshot` (:171), `test_runtime_rejects_include_and_exclude_together` (:218), `test_unknown_selected_skill_is_rejected` (:231), `test_selector_must_not_be_a_string` (:242).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'load_skill UniqueKeyLoader _BEHAVIORAL_FRONTMATTER_FIELDS'`

## Verdict
**Adopt** the string-typed unique-key YAML contract for any frontmatter-driven plugin identity. **Adopt** acknowledge-and-report for unsupported foreign fields. **Adapt** name rules to your registry; keep parity-with-directory as the selector truth anchor.
