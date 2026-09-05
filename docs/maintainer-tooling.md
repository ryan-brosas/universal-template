# Maintainer tooling

`universal-template` is a content and capability baseline. Python is not part of
ordinary installation, discovery, routing, model choice, policy review, or prose
review. It remains temporarily in small maintainer tools where deterministic
behavior earns the dependency.

## Retained

| Script | Class | Exact responsibility |
| --- | --- | --- |
| `skill-validator.py` | REQUIRED HARD CONTRACT | Strict YAML frontmatter, known-field types, invocation/visibility/kind invariants, name/directory identity, uniqueness, no legacy/symlink foundation tree, and complete referenced-file inventories. |
| `repo-hygiene.py` | REQUIRED HARD CONTRACT | Git-tracked publication paths, required files, whitespace, structured parsing, file-size bounds, vendor/session exclusions, portable paths, and credential patterns. |
| `web-reference-manifest.py` | REQUIRED HARD CONTRACT | Manifest types and enums, contained paths, referenced files, capture identifiers, timestamps, and credential patterns. |
| `pr-metadata.py` | REQUIRED HARD CONTRACT | The PR-title grammar consumed by label and release automation. |
| `install-prompts.py` | OPTIONAL COMPATIBILITY TOOL | Safe reconciliation for legacy host prompt surfaces; preserves unmanaged files and atomically derives adapters from Markdown. |
| `render-prompt.py` | OPTIONAL COMPATIBILITY TOOL | Single-pass prompt placeholder rendering for hosts without native prompts. |
| `runtime-capabilities.py` | OPTIONAL DIAGNOSTIC | Read-only aggregate environment report; native host inventories remain authoritative. |
| `github-audit.py` | OPTIONAL DIAGNOSTIC | Read-only GitHub configuration snapshot; direct `gh` output remains authoritative. |
| `skill-catalog.py` | GENERATED-ARTIFACT TOOL | Entry-only hot/cold sets, the complete AGENTS.md-plus-metadata static budget, optional search/stats, and separate generated catalogs derived from tracked filesystem/frontmatter. |

## Optional invocation-cost inventory

Run from the checkout being inspected (an explicit `SKILLS_ROOT` may select a
separate skill tree):

```bash
python3 scripts/skill-catalog.py invocation push-pr --json
python3 scripts/skill-catalog.py invocation --limit 10
```

Without a name, report the largest tracked loaders; an explicit name or folder
can inspect a machine-local skill. JSON is always an array. `--limit` must be
positive. Unknown names and unreadable reference Markdown return exit 2; size
alone never fails this diagnostic. No invocation-size limit is added to publication CI.

`loader_chars` counts Unicode characters in the complete `SKILL.md`, including
frontmatter; `loader_words` counts whitespace-separated words. References are
recursive `.md` files under that skill's `references/`, not shared cross-skill
links, scripts, assets, or every document linked by Markdown. The report gives
count, total characters, and the largest reference's relative path and size.
Symlinks are not followed; `skipped_reference_paths` identifies omitted entries.
An empty inventory has zero references and no largest reference.

These are on-disk sizes, not instructions to load all references or estimates of
actual task context. MCP profile/schema costs, invocation counts, and average
follow-up request growth in bytes remain `null` (unknown/not measured): the catalog
has no canonical per-skill runtime telemetry. It does not activate MCP, infer a
profile from prose, or treat absent observations as zero usage. Pair this inventory
with a scoped host probe or representative task comparison before claiming lift.

## Retired

- `policy-consistency.py`: interpreted natural-language policy with expanding
  regex and phrase fixtures. `template-maintenance` now reviews semantics.
- `style-lint.py` and `extensions/style-guard.ts`: enforced prose preferences
  mechanically. `house-writing-style` now guides model review.
- `catalog-quality.py` and `context-budget-baseline.json`: centralized semantic
  skill classes and heuristic context budgets. Invocation ownership now lives in
  each skill; the catalog is derived.
- `resolve-model.py`: encoded fixed role thresholds and ranking. The model now
  starts from task needs and live host inventory.
- `dead-code.py`: inferred usefulness from textual mentions. Maintainers inspect
  callers and relevance directly.
- `reference-retrieval-fixture.py`: tested policy phrases rather than runtime
  retrieval behavior.
- `legacy-skill-report.py`: phrase-based migration judgment with no hard
  publication contract.
- `foundation-validator.py`: mixed structural checks with semantic promotion
  phrases. Exact foundation metadata and references are covered by
  `skill-validator.py`.
- `conventional-commit.py`: duplicated PR metadata parsing and imposed commit
  prose style. The PR title remains the release-facing protocol.

## Model-owned decisions

Policy consistency, skill usefulness and overlap, prose quality, evidence trust
and sufficiency, ADOPT/ADAPT/OMIT decisions, model selection, and architectural
tradeoffs are reviewed from current source and runtime evidence. A deterministic
check should be added only when every valid implementation has the same
byte-level or structural answer.
