---
title: skill-catalog
summary: "Use when no visible pack clearly owns a task, a named technology needs a specialist, or selection seems wrong. Search playbook titles and summaries; read only the narrowest match."
kind: playbook
---

# Find the missing specialist

This is a fallback, not a phase before every task. A visible pack that clearly
owns the request wins. The canonical specialist inventory is the parent
`knowledge/playbooks/` directory, not a generated catalog.

1. For this template, read `../template-maintenance/README.md`; for authoring or
   auditing packs and playbooks, also read `../writing-skills/README.md`.
2. Search bounded playbook directory names and `README.md` titles/summaries using
   task nouns, languages, products or file formats. Inspect the best 1–3 matches.
3. Prefer the narrow operational owner. Named languages/frameworks use the
   matching practices playbook. Exact tools and formats use their specialist.
4. Read that `README.md`, then only references needed for the question. Resolve
   references and helpers from the selected playbook directory. If no procedure
   adds useful context, continue from project source instead of forcing a match.

For source-specific implementation evidence, read
`../../../skills/foundation-pack/SKILL.md` and choose one category, foundation and
capsule. The capsule's source pin and current source outrank historical summaries.

Missing usage telemetry is not evidence of disuse. Verify changed callers and
actual host discovery; new specialists remain playbooks linked from one existing
pack, not additional visible skills. See `../../../CONTRIBUTING.md`.
