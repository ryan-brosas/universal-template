---
title: cross-repo-source
summary: Use for broad investigations over indexed code, including the current repository, or external implementation research — delegate exploration, then verify decision-critical evidence.
kind: playbook
---

# Indexed and cross-repository source

## Core principle

Delegate exploration and synthesis; retain responsibility for decisions, edits
and proof. Prefer Sourcebot's `ask_codebase` for broad indexed-code questions so
search trails and dead ends stay out of the main context. Read only the decisive
source needed to act on its findings, not every file it investigated. Direct
retrieval remains preferable for narrow lookups.

Optimize the whole task: main-context consumption, total work, latency and error
risk. Delegation can save context without saving total inference cost or time.
An indexed answer is evidence-backed guidance, not authority over the working
tree. Sourcebot is the single persistent indexed cross-repository source; do not
co-load a second indexed code-graph server for the same question.

## Corpus

Sourcebot indexes a small deliberate corpus, not the public GitHub universe. The
corpus is an explicit repository list in the deployment's own configuration,
which lives outside this template together with the index and database.

- Default branches only. Add a long-lived branch explicitly, and only while a
  specific comparison needs it.
- Admission is earned: a repository joins after it repeatedly proves useful in
  cross-repository work, never automatically because one task touched it. Do not
  ingest every repository read during research.
- Group the corpus so it stays understandable: keep owned/core repositories
  distinct from inspiration repositories, and organize project-specific
  inspiration around the projects or domains that need it.
- A miss is the normal boundary, not a failure: discover the repository with
  GitHub, read the real source and tests, then decide about admission.

## Choose the route

| Question | Route |
| --- | --- |
| Known path, precise symbol or small factual lookup | Direct read, grep or symbol lookup |
| Broad ownership, execution flow, architecture or comparison across indexed code | Code Ask, including for an indexed current repository when revision coverage fits |
| Broad question depending on uncommitted changes or an unindexed branch | Local research agent when available; otherwise bounded local retrieval |
| Implementation outside the corpus | GitHub discovery and direct source, or a scoped research agent |
| Editing or proving working-tree behavior | Local source, Git, tests and focused probes |

Delegate early when breadth is apparent. If a narrow lookup expands into several
subsystems or competing implementations, hand off the bounded question with the
useful facts already found instead of continuing an unbounded manual search.
Do not first complete the investigation and then ask Code Ask to repeat it.

## Delegated investigation

1. Confirm the repository names and branch coverage with `list_repos` and, when
   needed, `list_branches`. Use known current coverage rather than repeating
   discovery gratuitously. An indexed baseline can orient local work, but cannot
   establish behavior of uncommitted changes or an unindexed branch.
2. Check the live tool schema and permissions. Some deployments describe
   `ask_codebase` as explicit-request-only. Respect that restriction and report
   it as a blocker to proactive use; changing this playbook does not change the
   server's tool description. Use direct retrieval or a local agent meanwhile.
   Model configuration and any supported description override belong to the
   deployment/host, not a speculative adapter in this template.
3. Give Code Ask a bounded research contract: the decision to inform, explicit
   `repos`, relevant subsystem, specific questions and exclusions. Set
   `visibility: PRIVATE`; do not include secrets or unnecessarily upload local
   source. Use the configured model unless the task justifies a supported choice.
4. Request a concise answer with an execution map, decisive source references,
   relevant tests, likely change points and unresolved questions. Distinguish
   source-backed findings from inference. Ask for the revision used if available;
   do not imply freshness it cannot establish. Do not request a full transcript.
   In the current schema, revision and length requests are prompt instructions,
   not enforced controls: there is no dedicated ref or output-length argument.
5. Inspect only the decision-critical source and tests, check relevant local
   differences, then implement and verify locally. A citation makes a claim
   inspectable; it does not establish its correctness or freshness. Do not
   recreate the delegated investigation merely to verify it.

Example request:

> Investigate how repository X invalidates cached permissions after role changes.
> Trace the write path through invalidation to subsequent authorization checks.
> Identify relevant tests and likely change points. Return a concise execution
> map, decisive file/line references, failure cases and unresolved questions.
> Distinguish source-backed findings from inference and report the revision used
> if available. Exclude unrelated architecture and the exploration transcript.

Bound follow-ups to a specific missing fact or corrected scope. If findings
conflict, read the disputed boundary directly. If the service is unavailable,
unconfigured or lacks coverage, switch routes and report the limitation. Avoid
recursive research loops; parallelize only independent questions, not duplicate
investigations of the same seam. Code Ask can take 60+ seconds; account for that
when a direct lookup would suffice.

## Direct retrieval

1. Confirm the repository name and its default branch with `list_repos`
   (optionally with `query`); note whether that exact branch is indexed. Pin that
   ref explicitly on every later retrieval call that supports it: a `grep`
   without a ref searches the default branch, while a later `read_file` can
   resolve a different revision, and trees can differ structurally between
   branches. Do not invent ref arguments for tools that lack them.
2. Narrow with `grep` (`groupByRepo: true` across many repos, `include` to filter
   file types) or `glob`; use `list_tree` to orient in an unfamiliar repository.
3. For a symbol, prefer `find_symbol_definitions` / `find_symbol_references` over
   text grep. Symbol matching is exact, so pass the precise identifier.
4. `read_file` the decisive file (paginate with offset/limit; output is capped)
   and read its direct tests. Use `list_commits` / `list_branches` when the
   index's own revision or history matters.
5. When `read_file` misses a path a `grep` just hit, re-run the grep with an
   explicit ref first; if the hit vanished entirely, it may have been a transient
   state while the index was actively re-ingesting that repository. Do not cite
   a hit you cannot read again. Convert a load-bearing hit into `read_file`
   output (repo, ref, path, lines) immediately.

## Verification and freshness

Verify decisions, not the entire search trail:

- Orientation findings may be used provisionally as navigation aids. Attribute
  delegated findings that have not been independently checked.
- Claims determining an edit require reading the decisive current source.
  Security, data-loss, compatibility and concurrency claims need relevant paths,
  tests and focused behavioral probes where practical.
- Results describe an indexed snapshot, not live code. Before treating an answer
  as current — especially for a repository just changed — compare the indexed
  commit with the live repository head using GitHub or direct Git
  (`git ls-remote <remote> <ref>`), not Sourcebot's own `list_commits`. Compare
  relevant working-tree changes as well. A branch name alone is not a pinned
  commit, and an index can advance during an investigation.
- If revision identity cannot be established, use the answer for orientation
  and explicitly qualify current-behavior claims. Do not check every remote head
  for a harmless architectural overview that does not require freshness.
- Absence claims state the search scope and index limits; a miss is not proof
  that an implementation does not exist.

Report the repository, revision when known, decisive files actually read, checks
actually run and coverage caveats. Keep edits and final proof local to the
working tree when implementing there.

## Inspiration and adaptation

Use one strong implementation per question. Compare it with the current project's
constraints and decide ADOPT / ADAPT / OMIT per concern; never blind-copy.
Provenance and licensing live in `../reference-driven-development/README.md`.
Code Ask may synthesize alternatives; the coding agent owns the adaptation
choice and verifies its decisive evidence. For a repository outside the corpus,
use GitHub to discover it and read it there.

## Evaluating routing changes

Use representative tasks, not phrase-matching tests of nuanced policy: a narrow
lookup should stay direct; a broad execution trace should delegate early; a
cross-repository comparison should return scoped evidence; branch divergence
should trigger local verification; missing or stale evidence should lead to a
fallback or qualification. Observe actual tool calls, not only a proposed route.
Compare main-context usage, elapsed time, total usage where exposed, correctness
and duplicated investigation. Success is less exploration in the main context
with equal or better decision quality, not a higher Code Ask call count. Report
unrun scenarios and runtime blockers rather than claiming policy text proves
behavior. Do not create a benchmark framework for a one-off policy change.
