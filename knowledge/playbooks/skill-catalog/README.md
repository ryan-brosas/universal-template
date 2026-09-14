---
title: skill-catalog
summary: "Use when no visible pack clearly owns part of a task, a named technology needs a specialist, or selection seems wrong. Search playbook titles and summaries; read the narrowest useful set."
kind: playbook
---

# Find the missing specialists

This is a fallback, not a phase before every task. Load a visible pack directly
when it clearly owns part of the request. For compound work, separate the active
subproblems by operational owner and select the smallest set of packs and
procedures that covers them. The canonical specialist inventory is the parent
`knowledge/playbooks/` directory, not a generated catalog.

1. For this template, read `../template-maintenance/README.md`; for authoring or
   auditing packs and playbooks, also read `../writing-skills/README.md`.
2. Search bounded playbook directory names and `README.md` titles/summaries using
   task nouns, languages, products or file formats. Inspect a bounded shortlist,
   not the whole catalog.
3. Prefer the narrow operational owner for each active subproblem. Named
   languages/frameworks use the matching practices playbook. Exact tools and
   formats use their specialist.
4. Read each selected `README.md`, then only the references needed for its part of
   the question. Resolve helpers from that playbook's directory and deduplicate
   cross-links by canonical path. If no procedure adds useful context, continue
   from project source instead of forcing a match.

Selection cardinality and ownership are separate: zero, one, or several packs
and procedures may be active, while each playbook remains linked from one
canonical cold index. When packs overlap, use each only for the decisions it
owns; the narrower procedure governs decisions inside its scope.

For a source-specific implementation question, read the relevant repository's
current source directly, or retrieve an indexed or external implementation with
`../cross-repo-source/README.md`. Source and tests outrank any summary.

Missing usage telemetry is not evidence of disuse. Verify changed callers and
actual host discovery; new specialists remain playbooks linked from one existing
pack, not additional visible skills. See `../../../CONTRIBUTING.md`.
