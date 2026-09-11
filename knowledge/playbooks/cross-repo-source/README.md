---
title: cross-repo-source
summary: Use when a code question spans repositories or needs an implementation not available locally — retrieve it with the indexed source capability (Sourcebot), then read the real source instead of a summary.
kind: playbook
---

# Cross-repository source

## Core principle

Retrieve the minimum source needed to answer a specific question, then read the
actual files and their tests. An indexed search is a fast map, not authority;
confirm findings in source before editing or claiming absence. Sourcebot is the
single indexed cross-repository source: never co-load a second code-graph server
for the same question.

## Corpus

Sourcebot indexes a small deliberate corpus, not the public GitHub universe. The
corpus is declared once as an explicit repository list in the deployment's
config (on this machine `~/sourcebot/config.json`); the deployment,
its index and its database live outside this template.

- Default branches only. Add a long-lived branch explicitly, and only while a
  specific comparison needs it.
- Forked and archived repositories are excluded; an owned repository is listed
  under its canonical upstream when the local fork carries no unique work.
- Admission is earned: a repository joins after it repeatedly proves useful in
  cross-repository work, never automatically because one task touched it.
- A miss is the normal boundary, not a failure: discover the repository with
  GitHub, read the real source and tests, then decide about admission.

## When to use / NOT

- **Use when:** locating a symbol or pattern across indexed repositories,
  comparing how another project implements a seam, or navigating an unfamiliar
  large tree where a broad local search would be slower or impossible.
- **NOT when:** the file or symbol is already known (read it directly); the
  question is local to the active project (filesystem search, Git, IDE/LSP
  suffice); or the implementation is outside the corpus and one direct read
  answers it.

## Workflow

1. `list_repos` (optionally with `query`) to confirm the repository name; note its
   default branch and whether the branch is indexed. Match the exact branch across
   pagination or a filtered query; never substitute the first returned branch.
   For readiness probes, require actual result records/counts, not a substring such
   as `match` (which also accepts “no matches”). Searchability and freshness are
   separate checks; a successful search does not prove a recent sync succeeded.
2. Narrow with `grep` (`groupByRepo: true` across many repos, `include` to filter
   file types) or `glob`; use `list_tree` to orient in an unfamiliar repository.
3. For a symbol, prefer `find_symbol_definitions` / `find_symbol_references` over
   text grep. Symbol matching is exact, so pass the precise identifier.
4. `read_file` the decisive file (paginate with offset/limit; output is capped)
   and read its direct tests. Use `list_commits` / `list_branches` when revision
   or history matters.
5. Report the repository, revision, and any coverage caveat. Results come from
   the index's snapshot, not live, and a search miss is not proof of absence.

## Inspiration and adaptation

Use one strong implementation per question. Compare it with the current project's
constraints and decide ADOPT / ADAPT / OMIT per concern; never blind-copy.
Provenance and licensing live in `../reference-driven-development/README.md`.
`ask_codebase` is a blocking AI summary — invoke it only when explicitly asked and
prefer direct tool calls.

## Verification

The claim names the file(s) read and the revision; symbol or call-graph claims are
confirmed by reading source; absence claims state the search scope and index limits.
After the MCP deployment was restarted, query from a fresh session: a pooled session
created before the restart fails with `Server not initialized`, which is a stale
session rather than a missing index.
