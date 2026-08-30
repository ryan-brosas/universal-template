---
name: web-reference
description: "Use when a live website or web page should be captured and studied as frontend, visual, layout, interaction, or design-system prior art for implementation."
---

# Web Reference

## Core Principle

A rendered website is evidence, the same way a cloned repository is evidence for code. Raw capture preserves what the site served and rendered; a normalized layer states what matters for this project. The current project stays the implementation and acceptance authority. A reference informs hierarchy, structure, spacing, typography, and behavior; it never defines requirements and is never pixel-copied.

## When to Use / NOT

- **Use when:** the user gives a URL as frontend or visual inspiration; design direction is unclear and discovery comes first; a frontend question needs rendered evidence (DOM, CSS, computed styles, screenshots, behavior); an existing web reference needs a refresh.
- **NOT when:** the task is backend implementation (repository reference path); the change is small and the current codebase answers it (source, edit, verify); the user only wants content facts (web search).

## Workflow

1. **Inspect the current project first.** Tokens, components, accessibility rules, and product requirements outrank any reference. Capture fills gaps; it does not override the design system.
2. **Pick the cheapest sufficient mode** (`references/capture.md`): `quick` (one region), `page` (one URL), `site` (bounded same-host crawl), `deep` (design-system reverse engineering, earned by the request), `refresh` (new dated capture of a known reference).
3. **Capture with capability detection.** Static page: HTTP fetch or the SingleFile CLI. Rendered or scripted pages: `browser-harness-js` (CDP). Whole-site archive: `browsertrix-crawler` in Docker emitting WACZ.
4. **Respect access rules.** HARD-GATE: never bypass authentication or rate limits, never store credentials, use only the user's authorized session. Scope rules in `references/scope.md` are load-bearing: same host, bounded pages, no destructive routes.
5. **Extract structure** (`references/extraction.md`): rendered HTML, network CSS plus CSSOM, CSS custom properties, selected computed styles, repeated patterns. Call unknown boundaries "patterns", not components. Keep raw evidence next to the extracted layer.
6. **Normalize into a bundle** (`references/storage.md`): `reference/web/<host>/` with a decision-oriented `REFERENCE.md` and a `manifest.json` that records source, capture date, scope, evidence inventory, and coverage gaps. Small references stay small.
7. **Declare gaps.** Partial capture (desktop only, blocked route, missing hover states) goes into `coverage_gaps`. A partial capture is never presented as complete knowledge.
8. **Consume, do not imitate.** Implementation runs through `reference-driven-development`: ADOPT / ADAPT / OMIT per concern against current requirements. Media decisions follow `references/media.md`: CSS first, existing assets second, generated originals only when needed.
9. **Validate the bundle:** `python3 ~/.agents/scripts/web-reference-manifest.py reference/web/<host>` must exit 0 with P0 = 0.
10. **Stop** when the bundle answers the current question, declares its gaps, and validation passes. Deeper capture waits for a named gap.

## Red Flags

- **Never** crawl unbounded or touch destructive routes (logout, delete, checkout, account changes); `references/scope.md` owns the exclusions.
- **Never** copy logos, brand illustrations, marketing copy, or proprietary media; capture media roles, not assets (`references/media.md`).
- Do not overwrite an earlier capture; `refresh` writes a new dated capture and reports changes.
- Generated media stays out of `reference/web/`; it belongs to the project asset directory.
- A captured site never auto-promotes to a skill or foundation. It stays a project-local reference.
- A design tool (OpenDesign or similar) is an optional workspace on top of captured evidence; the live site stays the source evidence for capture questions.

## Verification

- `python3 ~/.agents/scripts/web-reference-manifest.py reference/web/<host>` exits 0; `REFERENCE.md` states ADOPT / ADAPT / OMIT and coverage gaps; `manifest.json` parses with source, captured_at, and scope.
- Frontend work built from the reference is verified in the browser with the `cdp` skill: render, responsive viewports, console, network. The current project's gates decide acceptance, not the reference.

## References

- `references/capture.md`: tool ladder, verified commands per mode, auth and session rules
- `references/scope.md`: bounded crawling, URL normalization, exclusions, limits
- `references/extraction.md`: CSS, DOM, style, and pattern extraction with exact snippets
- `references/media.md`: media roles, CSS-first rule, image generation, provenance
- `references/storage.md`: bundle layout, manifest schema, versioning, storage policy
