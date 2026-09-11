---
title: cross-repo-source
summary: Use when a code question spans repositories or needs an implementation not available locally — retrieve it from indexed source (Sourcebot), then read the real source and tests instead of a summary.
kind: playbook
---

# Cross-repository source

## Core principle

Retrieve the minimum source needed to answer a specific question, then read the
actual files and their tests. An indexed search is a fast map, not authority;
confirm findings in source before editing or claiming absence. Sourcebot is the
single indexed cross-repository source: never co-load a second code-graph server
for the same question.

Retrieval and reasoning belong to the coding agent. Search, read the decisive
source and tests, and reason directly; do not route the question through a
delegated "ask the codebase" step that produces another model's interpretation.

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

## When to use / NOT

- **Use when:** locating a symbol or pattern across indexed repositories,
  comparing how another project implements a seam, or navigating an unfamiliar
  large tree where a broad local search would be slower or impossible.
- **NOT when:** the file or symbol is already known (read it directly); the
  question is local to the active project (filesystem search, Git, IDE/LSP
  suffice); or the implementation is outside the corpus and one direct read
  answers it.

## Workflow

1. Confirm the repository name and its default branch with `list_repos`
   (optionally with `query`); note whether that exact branch is indexed.
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

## Verification

The claim names the file(s) read and the revision; symbol or call-graph claims are
confirmed by reading source; absence claims state the search scope and index limits.
