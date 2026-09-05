# Template effectiveness: local changes and evidence

This is a bounded investigation record, not an operating procedure or a new gate.
The starting worktree already contained substantial unrelated changes. Local
implementation preserved them and did not modify live host configuration. The
subsequent publication branch was isolated atop newer origin/main; its upstream
fixtures, invocation diagnostics and native-discovery improvements were retained.
Host counts and model trials below describe the earlier local investigation, not
a fresh benchmark of the rebased publication tree.

## What became easier

- `AGENTS.md` keeps authority, safety and verification, while saying that skills
  supply context and shortcuts and the model owns the approach. It points to the
  adjacent cold skill tree without requiring a catalog, router or setup phase.
  It remains within the existing 3,000-character limit (2,993 characters).
- Project entry no longer requires a complete onboarding report or running every
  discovered command before implementing the request.
- Migration guidance distinguishes public consumers from private callers changed
  together. Codemods, compatibility windows, runtime warnings and feature flags
  are options with costs, not universal prerequisites. Binding-aware transforms
  and real consumer verification remain.
- Security guidance focuses on the relevant boundary and non-obvious failure
  modes instead of prescribing an auth, dependency and header overhaul for every
  security task. Test-first guidance accepts existing failure evidence and useful
  characterization tests instead of rejecting every test that initially passes.
- `practices-to-ci` no longer mandates Python scripts or carries an obsolete
  template CI inventory. Existing project tools come first; objective checks
  still need a worthwhile failure class.
- `fabric-native-execution` points to installed host contracts rather than copying
  provider methods and runner semantics. `source-driven-development` no longer
  requires a separate evidence router or delivery checklist before using a known
  source. Exact capsule pins and direct source reads remain useful shortcuts.
- `skill-catalog` now advertises cold expertise for an ordinary knowledge gap,
  not only explicit catalog requests. The repaired NocoDB capsule has a precise
  topic-map cue for LongText/NUL handling; the capsule's own pin is authoritative
  when the foundation contains evidence from several revisions.
- Implementation/planning prompts no longer duplicate the constitution or imply
  that every mechanically expressible preference deserves a new gate.

No script was deleted merely to reduce file count. The affected script
prerequisites were in prose; removing useful implementation would not have helped.

## Integrity repairs

`skill-validator.py` owns strict frontmatter parsing, also used by
`skill-catalog.py`. PyYAML exceptions previously echoed arbitrary source values.
Diagnostics now retain error class and numeric location without parser snippets,
keys or invalid metadata values. Chained YAML exception display is suppressed.
Malformed enum containers also report validation errors instead of crashing.
Synthetic canaries exercise syntax errors, duplicate keys, unknown tags, NULs and
invalid metadata. Catalog CLI fixtures cover permissive discovery and failing
publication paths without leaking input on stdout or stderr.

`repo-hygiene.py` previously classified NUL-bearing Markdown as binary and skipped
its safety scan without failing. Declared text now fails on NUL, including
uppercase suffixes and vendored Markdown, while decodable content still receives
credential scanning. Invalid UTF-8 also fails for declared text. Existing binary
controls, bounded reads and explicitly partial large-file scans remain intact;
this is not a complete binary-secret scanner.

Both new regression classes failed before their production fixes and passed
afterward. No real credentials were used in the tests.

The NocoDB LongText regex was repaired byte-for-byte against
[`f7513664f3f3b7286023a7e832a8333808f7557b`, lines 1717–1720](https://github.com/nocodb/nocodb/blob/f7513664f3f3b7286023a7e832a8333808f7557b/packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts#L1717-L1720).
The capsule remains a condensed excerpt; unrelated historical claims were not
revalidated or rebuilt.

## What this host actually loaded

Installed Pi 0.85.1 `DefaultResourceLoader`, using current global settings and
this repository as cwd, was probed with extension execution disabled. It loaded
371 skills in total: 355 from this template, of which 41 were visible and 314
hidden; 194 were foundations. The constitution and revised catalog description
were present. This is loader evidence, not a claim about every extension's final
prompt modifications. The active session's advertised skills also include the
catalog; already-running sessions can retain older descriptions until reloaded.

**Hidden does not mean unscanned.** Pi honors hidden metadata for the prompt but
still parses cold skill files. A separate in-memory configuration excluded the
canonical skill root and force-included each tracked hot `SKILL.md`:

```text
skills: ["!<absolute-canonical-skills-root>/**",
         "+<absolute-hot-skill-file>", ...]
```

Using the native settings/resource loader, this produced exactly the intended 32
hot template skills, zero hidden template skills and zero diagnostics. No live
settings or symlink inventory was written. Directory enumeration still happens;
this proves body-loading selection, not zero filesystem traversal. Intentional
host extras must be preserved when applying such a filter. On hosts without
verified native filtering, the filtered symlink-view fallback remains available.

Read-only mount inspection and `install-prompts.py --check` also found:

- Claude and Codex still link the unfiltered canonical skill root. Their current
  payloads were not captured; visibility behavior remains unverified here.
- The Pi `style-guard.ts` extension link points to a retired, missing target.
- Gemini's generated `compile-skill` and `inspo` adapters were stale. This work's
  changed `implement-work` and `plan-work` sources also need adapter regeneration.
- The local, untracked `coderabbit` prompt was not mounted across the audited
  global prompt surfaces. The repo-scoped Pi loader nevertheless found a
  `coderabbit` prompt; a local loader result is not proof of global installation.

Applying native skill filters, removing the provably owned broken extension link,
and reconciling owned prompt adapters would affect user-wide future sessions.
Those live changes were not authorized or performed. Markdown symlinks already
follow repository body edits; generated adapters do not. Repository correctness
alone does not close this deployment gap.

## Representative model tasks

Native Pi 0.85.1 with authenticated `openai-codex/gpt-5.6-luna`, medium thinking,
and read/bash/edit/write/grep/find/ls ran separate temporary projects. No template
scripts, MCP service, generated catalog or host extensions were required. The
projects had real Node tests and an unrelated uncommitted user edit. Independent
post-run assertions checked behavior and preservation, rather than trusting the
model's final report. Runs had up to 12 minutes to finish and needed no user
intervention.

| Task | Starting guidance | Revised guidance | What this establishes |
| --- | --- | --- | --- |
| Private helper rename with consumer update | 17 tool calls, correct | 18 tool calls, correct | Both preserved output and user edits without codemods, migration artifacts or new dependencies. No efficiency gain demonstrated. |
| Airtable/PostgreSQL NUL repair using cold NocoDB evidence | 29 calls, 13 reads, 96 seconds | Final revision: 23 calls, 10 reads, 69 seconds | Both passed project tests and independent Unicode/NUL/row-preservation assertions and cited the correct pinned file. The final revision reached the capsule with less work in this trial. |

The first exploratory cold-task runs could inspect sibling experiment artifacts;
they are excluded from the table. Corrected runs allowed only the fixture and
read-only context (plus optional public pinned source fetches). Isolation was
instruction-based, not an OS filesystem sandbox; the retained traces were inspected.
The first revised
cold run was worse: 33 calls and 111 seconds, including a regex error. Inspection
showed weak topic cues, broad searches and unnecessary source-routing reads.
The final revision added the precise capsule cue and shortened the evidence skill;
only that changed path was rerun. Its 23-call run had no tool errors. The baseline's
one nonzero tool result was an intentional failing regression test, not wasted
work. Neither run repeated a file read, so no repeated-read improvement is claimed.

These are small, non-blinded trials, not a benchmark or proof of general model
improvement. The rename pilot shared an experiment parent, though its trace stayed
within the project; treat that comparison cautiously too. Cold evidence used the
repaired capsule in both arms. Task completion and easier retrieval are observed;
broad skill lift, other models, full extension stacks and other hosts remain
uncertain. No permanent evaluation framework or score gate was introduced.

## Helpers that still earn their place

- Strict metadata/reference validation and tracked-file hygiene protect objective
  publication boundaries, including the repaired error and byte-handling cases.
- Prompt installation/rendering handle derived formats and safe ownership-aware,
  atomic reconciliation. They remain optional, not a setup dependency for work.
- Catalog generation derives optional human views and publication context bounds;
  native file search remains sufficient for discovery.
- MCP configuration protects portable, scoped activation and secret/path handling.
  Web-reference manifest checks protect capture identifiers and contained paths.
  PR metadata parsing serves the actual release protocol. None is an ordinary
  project-entry requirement.

## Validation scope

Relevant checks: strict skill validation and selftest; catalog selftest and CLI
fixtures; context budget and generated parity; hygiene selftest, committed
fixtures and tracked publication scan; prompt repository shape, atomic installer
selftest and renderer selftest; changed-line whitespace. The read-only live mount
check is expected to fail for the deployment gaps above. Unrelated crew, MCP,
CDP and workflow changes in the starting worktree are outside this verification.

Before publication, all 17 commands in the rebased branch’s `CONTRIBUTING.md`
passed in the isolated worktree. That tree has 28 hot skills and 10,128 combined
static characters, reflecting newer upstream changes rather than this trial’s
original context surface. No model timing comparison was rerun on that new base.
