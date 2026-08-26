---
name: pi-template-foundation
description: "Use when porting or building skill-pack catalogs, progressive-disclosure routers, agent-infrastructure CI gates, repo hygiene ladders, conventional-commit checks, dependency-cycle detection, inspiration-repo smoke harnesses, or mutation-authority guards for prompt/skill/template repositories — clone-and-start agent workspaces whose product surface is configuration, not application code."
---
# pi-template: agent-template governance foundation

## Use this for
Use when porting or building skill-pack catalogs, progressive-disclosure routers, agent-infrastructure CI gates, repo hygiene ladders, conventional-commit checks, dependency-cycle detection, inspiration-repo smoke harnesses, or mutation-authority guards for prompt/skill/template repositories — clone-and-start agent workspaces whose product surface is configuration, not application code. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/catalog-integrity-gate.md` — prove a skill catalog has no drift between membership JSON, ledger, router listings, and disk.
- `references/skill-quality-gate.md` — catch bad skill metadata without false alarms: errors vs warnings split, prefix-overlap near-duplicate detection, essentials indexing.
- `references/repo-hygiene-ladder.md` — mechanically enforce whitespace/EOF/encoding/size/secrets/typo/orphan discipline while exempting named append-only records.
- `references/dead-code-scan.md` — what "dead code" means when membership is data: unreferenced scripts and unlisted skill dirs, routers/foundations exempt.
- `references/inspo-test-runner.md` — smoke-test third-party inspiration suites through a uv venv extras ladder before building foundations on them.
- `references/mutation-guard-config.md` — configure mutation authority so writes stay gated without any application runtime (enforce vs audit duality).
- `references/ast-cycle-detector.md` — minimal stdlib-only circular-import detector via AST adjacency and DFS.
- `references/commit-subject-gate.md` — enforce conventional-commit discipline over git history and PR titles, and avoid the twin-grammar drift between the two validators.

## Capsule map
- **Catalog integrity** — `catalog-integrity-gate`: three-way set equality packs.json members ↔ manifest retained ↔ router bullet listing ↔ disk, with a live-vs-changelog scan boundary for historical state rows.
- **Metadata quality** — `skill-quality-gate`: duplicate names/descriptions hard-fail, orphaned references warn, near-duplicate descriptions by >60% prefix overlap of the shorter, essentials must exist AND be indexed in their README.
- **Hygiene ladder** — `repo-hygiene-ladder`: skip-listed walk enforcing trailing-whitespace (first hit), EOF newline, mixed endings, smart quotes/ligatures, >1MB cap with ONE named exemption, JSON/TOML/YAML validity, lightweight secrets regexes, prose typos, orphaned images, scratch files, submodule ban.
- **Template dead code** — `dead-code-scan`: dead = script never referenced by any yml/md/py/toml/cfg text, or skill dir absent from packs∪manifest name sets; pack-* routers and *-foundation leaves exempt as drain-managed.
- **Inspo smoke runner** — `inspo-test-runner`: uv venv → editable install ladder `.[test]`→`.[dev]`→`.`→pytest stack → `pytest -q` with import-heavy dirs ignored; exit code 5 surfaced as NO TESTS, a distinct outcome from FAIL.
- **Mutation authority** — `mutation-guard-config`: `schema.mode: enforce|audit`; enforce demands hypothesize→verify→commit in one executor turn with declared files and postconditions; audit/off/untrusted demands explicit per-mutation approval; research commands stay read-only.
- **Import cycles** — `ast-cycle-detector`: resolve module names from paths, exact-or-prefix internal-import matching, DFS stack-based cycle reporting outside skip dirs.
- **Commit subjects** — `commit-subject-gate`: two-stage grammar (broad `[a-z]+` regex then `ALLOWED_TYPES` membership with a sorted-set self-documenting error) over `git log -10` at the script-derived repo root, wired only in CI check.yml; documents the un-cross-checked pr-title.yml twin alternation (no `wip`) as the drift anti-pattern.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-template (MIT), `foundations-sync@37e9bc1736b7`; Codebase Memory project `pi-template` — FULL reindex at this pass: ready, 62262 nodes / 63798 edges at the pinned HEAD, parse_partial=4 (markdown work-record files only, none cited), skipped=0. Caveat: the previously pinned 7752-node generation was stale (served deleted `scripts/*.mjs` ghost symbols); always verify a pin-known symbol after index_status.

## Full view (memory graph)
Revalidate `pi-template` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the gate/check contracts, parity invariants, and error-vs-warning splits; adapt paths, catalog names, and stdlib choices to the host runtime; omit Pi-host specifics (`fabric_exec`, Pi session memory, Veda lanes), the five prompt workflows, the farmed `tests/harness/*` fixtures (their provenance belongs to other repos' foundations), and browser-tools/deploy utilities.
