---
name: humanizer-foundation
description: Use when building or porting an agent skill whose product is a Markdown prompt corpus — packaging one root SKILL.md for multiple agent hosts, CI-enforced cross-file consistency (three-way version parity, ordered-list vs complete-set pattern numbering, exact-string style rules), fail-loud zero-dependency package validators with imperative fix-naming messages, single-skill layout gates (rglob singleton, symlink refusal, prompt line budget), or the humanize-rewrite fact-integrity loop (two-question audit, mode-keyed return) with its 35-pattern false-positive boundary — capsule-v2 source maps with decisive excerpts and graph retrieval.
---

# Humanizer: foundation for Markdown-prompt skill packages

## Use this for
Use when building or porting an agent skill whose product is a Markdown prompt corpus — especially packaging one root SKILL.md for multiple agent hosts, CI-enforced cross-file consistency (versions, pattern numbering, style rules), fail-loud zero-dependency package validators, or the humanize-rewrite fact-integrity loop itself. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/humanize-rewrite-fact-integrity-loop.md` — how does the rewrite loop change prose without drifting a single fact?
- `references/pattern-taxonomy-false-positive-boundary.md` — which surface patterns flag AI prose, and what never counts as proof alone?
- `references/validator-fail-loud-message-ladder.md` — how does a zero-dependency validator fail first with a message that names the fix?
- `references/frontmatter-portability-gate.md` — which YAML frontmatter shape stays portable across agent hosts?
- `references/three-way-version-parity-set.md` — how do three files agree on one version with a missing-key trap?
- `references/single-skill-shape-gate.md` — what physical package shape survives plugin loaders and symlink incidents?
- `references/cross-file-numbering-and-rules-parity.md` — how do skill and README stay number-complete and rule-present without sharing order?
- `references/ci-triple-validation-gate.md` — which three independent checks gate a prompt-only repo in CI?

## Capsule map
- **Prompt-corpus plane** — `humanize-rewrite-fact-integrity-loop`: mark → draft → two-question audit (AI-sound? fact delta?) → final; unsupported addition OR lost claim is an error; three return modes keyed by input type.
- **Prompt-corpus plane** — `pattern-taxonomy-false-positive-boundary`: 35 numbered patterns in five category groups; a single tell proves nothing — stacked tells are evidence; quoted/title/proper-name text is exempt; a user writing sample overrides the rules (incl. dash-rate matching).
- **Package-validation plane** — `validator-fail-loud-message-ladder`: linear module-level gates; every failure is `SystemExit(<imperative fix-naming message>)`; success prints one sentinel line; zero external dependencies.
- **Package-validation plane** — `frontmatter-portability-gate`: anchored non-greedy frontmatter extraction; `compatibility:` / `allowed-tools:` banned so one prompt serves every host.
- **Package-validation plane** — `three-way-version-parity-set`: `metadata.version`, FIRST README bold entry, and plugin.json version must collapse to a set of size 1; `str(get(..., ""))` makes a missing key loud.
- **Package-validation plane** — `single-skill-shape-gate`: exactly one regular root `SKILL.md` (rglob set equality + symlink refusal), plugin pointer `skills: ["./"]`, prompt budget ≤500 lines.
- **Package-validation plane** — `cross-file-numbering-and-rules-parity`: SKILL pattern headings are the ORDERED list [1..35]; README table rows are the COMPLETE SET {1..35} (category tables are intentionally out of order); six exact plain-language strings must appear in AGENTS.md.
- **Distribution/CI plane** — `ci-triple-validation-gate`: self validator + pinned `skills@1.5.20 add . --list` discovery check + `claude plugin validate .`, all under `contents: read`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Humanizer (MIT declared in plugin.json, marketplace.json, SKILL.md frontmatter, and README License section; **no LICENSE file exists at the pin** — treat reuse as citations-only), `main@e2e92e7b4b8229253ed5c8e81dc65463fdeddda5` (v2.11.2); Codebase Memory project `humanizer` (FULL index, gen 2026-08-26T01:41:50Z, 150 nodes / 205 edges, parse_partial 0, skipped 0; check_index_coverage no_recorded_issue ×8 cited paths).

## Full view (memory graph)
Revalidate `humanizer` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Known graph shape: only ONE real function node exists (`require_match`) — the rest of the executable surface is module-level statements exposed as Variable nodes, and BM25 text queries over Section nodes can return zero rows, so enumerate Sections by label and code by name/qn pattern instead.

## Boundaries
Adopt the fail-loud gate pipeline, parity algebra (set-size version agreement, list-vs-set numbering), symlink/layout hygiene, and the fact-integrity rewrite loop as pure contracts. Adapt the exact gate messages, the 500-line budget, and the six plain-language strings to your own house style — the mechanism transfers, the literals are house rules. Omit the Claude-plugin marketplace projection (`marketplace.json`, `/plugin install` flow) and the skills.sh install badges unless you ship to those same hosts; omit Wikipedia attribution only if your pattern corpus has a different upstream.
