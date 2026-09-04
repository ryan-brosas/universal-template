---
name: web-reference
description: "Use when a live website or web page should be captured and studied as frontend, visual, layout, interaction, or design-system prior art for implementation."
invocation: manual
disable-model-invocation: true
---

# Web Reference

## Core Principle

A rendered website is evidence. The current project's requirements and runtime
behavior remain acceptance authority. Capture only what answers the active
question, preserve provenance, and separate observed facts from adoption choices.

## When to Use / NOT

- **Use when:** the user provides visual inspiration, design direction needs
  evidence, or implementation depends on current rendered behavior.
- **NOT when:** project source already answers the question, the task is backend
  only, or a normal web search is sufficient.

## Workflow

1. Inspect the current project's tokens, components, accessibility rules, and
   requirements first.
2. Choose the smallest useful capture mode from `references/capture.md`.
3. Capture through available native HTTP or browser capabilities. Respect auth,
   rate limits, destructive-route exclusions, and the user's authorized session.
4. Store source URL, capture time, scope, paths, and known gaps in
   `manifest.json`; keep `REFERENCE.md` concise and evidence-linked.
5. Inspect the manifest with native JSON and filesystem tools. Confirm exact
   field types, enum values, path containment, referenced files, and credential
   hygiene. The optional `web-reference-manifest.py` maintainer tool checks only
   these hard contracts.
6. Judge coverage and trust from the actual question and evidence. Record ADOPT,
   ADAPT, or OMIT only when implementation makes that decision.
7. Verify resulting work in the browser and against project tests.

## Red Flags

- Unbounded crawling, auth bypass, destructive routes, or stored credentials.
- Treating a scope label as proof that evidence is sufficient.
- Mechanically deciding trust, visual quality, or ADOPT / ADAPT / OMIT.
- Copying brand assets or promoting a capture automatically.

## Verification

The manifest parses; declared paths stay inside the bundle and exist; capture
identity and credentials satisfy the exact contract. The model separately
reports substantive coverage, evidence limits, and implementation decisions.

## References

- `references/capture.md`, capture modes and capability ladder.
- `references/scope.md`, crawl boundaries and exclusions.
- `references/extraction.md`, DOM and style extraction.
- `references/media.md`, media roles and provenance.
- `references/storage.md`, bundle structure and manifest fields.
