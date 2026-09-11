---
name: template-maintenance
description: "Use when auditing or maintaining this .agents/universal-template repository—especially failed or wrong skill selection, AGENTS.md, prompts, skills, templates, MCP declarations, or publication tooling; review semantics and run only relevant exact checks."
invocation: manual
disable-model-invocation: true
---

# Template Maintenance

## Core Principle

The model owns meaning. Deterministic checks own only facts that follow exactly
from source bytes, filesystem state, Git state, or runtime output.

## When to Use / NOT

- **Use when:** changing this template's canonical content or maintainer tools.
- **NOT when:** ordinary work in another repository, or when a direct project
  test already owns the acceptance boundary.

## Workflow

1. Inspect the current diff, nearby owners, callers, and any unmanaged changes.
2. Review changed policy, skills, prompts, and docs together for semantic
   consistency. Judge relevance, overlap, stale artifacts, prose quality, and
   whether each instruction still earns its place.
3. Ground factual claims in current source, Git, host inventory, and runtime
   output. Treat session history as evidence, never current truth.
4. Inspect metadata, names, references, intended host visibility, paths, and
   credential hygiene directly. Use existing focused tests when executable
   helpers change; no catalog generation or custom publication gate is required.
5. Separate hard failures from judgment calls. Fix objective failures; explain
   semantic tradeoffs with evidence instead of inventing a regex proxy.
6. Preserve unrelated files and report the commands that actually ran and their
   real results.
7. Recommend deleting a check when it duplicates reliable model review and has
   no objective contract to prove.

Stop when the affected content is coherent, relevant hard contracts pass, and
remaining uncertainty is reported.

## Red Flags

- Encoding nuanced policy or prose judgment as phrase tables.
- Running every historical script because an old checklist names it.
- Treating generated catalogs, projections, or diagnostics as ground truth.
- Publishing vendor runtime installs, session logs, private paths, or secrets.
- Replacing retired Python policy machinery with another language framework.

## Verification

The report names changed ownership boundaries, relevant hard checks and output,
semantic decisions made by review, preserved unrelated changes, and unresolved
uncertainty. Never claim a pass that was not observed.

## References

- `../../CONTRIBUTING.md`, content review and retained helper checks.
