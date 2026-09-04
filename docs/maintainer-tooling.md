# Maintainer tooling

`universal-template` is a content and capability baseline. Python is not part of
ordinary installation, discovery, routing, model choice, policy review, or prose
review. It remains temporarily in small maintainer tools where deterministic
behavior earns the dependency.

## Retained

| Script | Class | Exact responsibility |
| --- | --- | --- |
| `skill-validator.py` | REQUIRED HARD CONTRACT | One-tree frontmatter, invocation/visibility/kind invariants, name/directory identity, uniqueness, no legacy/symlink foundation tree, and complete referenced-file inventories. |
| `repo-hygiene.py` | REQUIRED HARD CONTRACT | Required paths, whitespace and EOF bytes, JSON/YAML/TOML parsing, file-size bounds, portable MCP paths, and obvious credential patterns. |
| `web-reference-manifest.py` | REQUIRED HARD CONTRACT | Manifest types and enums, contained paths, referenced files, capture identifiers, timestamps, and credential patterns. |
| `pr-metadata.py` | REQUIRED HARD CONTRACT | The PR-title grammar consumed by label and release automation. |
| `install-prompts.py` | OPTIONAL COMPATIBILITY TOOL | Safe reconciliation for legacy host prompt surfaces; preserves unmanaged files and derives adapters from Markdown. |
| `render-prompt.py` | OPTIONAL COMPATIBILITY TOOL | Single-pass prompt placeholder rendering for hosts without native prompts. |
| `runtime-capabilities.py` | OPTIONAL DIAGNOSTIC | Read-only aggregate environment report; native host inventories remain authoritative. |
| `github-audit.py` | OPTIONAL DIAGNOSTIC | Read-only GitHub configuration snapshot; direct `gh` output remains authoritative. |
| `skill-catalog.py` | GENERATED-ARTIFACT TOOL | Optional kind-aware search/stats plus separate operational-skill and foundation catalogs derived from filesystem/frontmatter. |

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
