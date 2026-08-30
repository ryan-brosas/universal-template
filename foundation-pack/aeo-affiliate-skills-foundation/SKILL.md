---
name: aeo-affiliate-skills-foundation
description: Use when porting agent skill-collection machinery from aeo-affiliate-skills — CLI-supervised localhost daemons with three-tier liveness reuse, idle self-shutdown lifecycle, TTL cache key namespacing, wide-page client-side filter adapters, markdown-corpus→registry generation coupled to invariant tests, executable documentation vocabulary contracts, pattern-grep skill eval harnesses, and agent-facing self-install bootstrap skills.
disable-model-invocation: true
---

# aeo-affiliate-skills: Agent Skill-Collection Foundation

## Use this for
Use when porting or building: an instant-response CLI backed by a spawn-on-demand local daemon; daemons that manage their own port/state/idle lifecycle; response caches shared across CLI invocations; client-side filtering over upstream APIs that lack filter support; machine-checked catalogs generated from a markdown corpus; documentation-as-test vocabulary guards; behavioral evals for prompt-skills without a test framework; or a skill that bootstraps its own compiled binary. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/cli-daemon-reuse-ladder.md` — how does a thin CLI get ~100ms responses by reusing a daemon it may have to start?
- `references/daemon-idle-self-lifecycle.md` — how does the daemon own its port, state file, and idle shutdown without leaking either?
- `references/ttl-cache-key-namespacing.md` — how are responses cached across requests, and which results must never be cached?
- `references/wide-page-client-filter.md` — how do you support filters the upstream API cannot evaluate server-side?
- `references/registry-invariant-pipeline.md` — how does a markdown skill corpus stay in verified sync with registry.json?
- `references/doc-vocabulary-contract-tests.md` — how do you stop field-name drift between docs, client code, and a renamed upstream?
- `references/pattern-grep-skill-evals.md` — how do you behavior-test prompt-skills with zero test framework?
- `references/agent-self-install-bootstrap.md` — how does an agent skill install and build its own tool on first use?

## Capsule map
- **Daemon-backed CLI** — `cli-daemon-reuse-ladder`: state-file → signal-0 pid → 1s HTTP health, spawn-on-miss, 200ms×5s startup poll, compiled-vs-source server path branch.
- **Daemon self-lifecycle** — `daemon-idle-self-lifecycle`: probe-bind port scan 9500–9510, state publication `{port,pid,token,started}`, idle timer reset on every request, deferred `/stop` exit, cleanup unlinks state swallow-errors.
- **Shared TTL cache** — `ttl-cache-key-namespacing`: lazy 5-min expiry-on-read, evict-oldest at 200 entries, per-endpoint key namespaces; `/search` caches empties while `/info` caches only non-empty.
- **Client-side filter adapter** — `wide-page-client-filter`: widen page to max(limit,100), apply unsupported filters locally, slice back; camelCase→snake_case adapter with defaulted fields; separate match-vocabulary vs display-vocabulary maps.
- **Registry pipeline** — `registry-invariant-pipeline`: stage-ordered corpus walk, hand-rolled frontmatter subset parser, tools merge precedence, and the de-facto `name === slug` invariant coupling generator to its invariant test.
- **Doc contract tests** — `doc-vocabulary-contract-tests`: runnable assertions pinning normalized field names into docs, banning retired synonyms by exact string, and guarding against retired API hosts.
- **Skill eval harness** — `pattern-grep-skill-evals`: embed whole SKILL.md + user prompt in one model call, judge by case-insensitive all-pattern grep, timeout→skip, timestamped run log, non-zero exit on failures.
- **Self-install bootstrap** — `agent-self-install-bootstrap`: project→user binary probe ladder, NEEDS_SETUP sentinel, approval-gated build, bun fallback.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
aeo-affiliate-skills (MIT), `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory project `aeo-affiliate-skills` (full mode, 2509 nodes / 2827 edges, generation 2026-08-25T08:24:56Z; parse_partial ×2 uncited HTML templates: bio-link.html L6/261, comparison.html L390; skipped=0).

## Full view (memory graph)
Revalidate `aeo-affiliate-skills` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the lifecycle/cache/filter/contract behaviors as portable contracts; adapt Bun-specific primitives (`Bun.serve`, `Bun.spawn`, single-file compile) and the fixed openaffiliate.dev vocabulary to your host; omit the affiliate-marketing content corpus itself, the hardcoded `Affitor` branding/author fields, and the token field written to state but never verified (add real auth if your loopback daemon leaves localhost).
