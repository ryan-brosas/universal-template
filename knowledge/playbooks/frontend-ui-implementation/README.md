---
title: frontend-ui-implementation
summary: Use when implementing or reviewing production frontend UI details—typography, font sizing, spacing, forms, validation, navigation, loading and empty states, visual hierarchy, responsive tables, icons, charts, and interaction feedback—from HTML/CSS or component code.
kind: playbook
---

# Frontend UI Implementation

## Core Principle

Translate interface intent into explicit tokens, semantic markup, complete component states, and rendered evidence. Preserve the PDF’s concrete starting values where useful, but label them defaults—not standards—and verify them against real content, project conventions, WCAG targets, devices, and user settings.

## When to Use / NOT

- **Use when:** coding or reviewing the visual and interaction details of a web frontend, including “make this UI polished/readable/responsive,” typography, forms, navigation, state feedback, and data presentation.
- **NOT when:** diagnosing which user problem to solve (`ui-ux-iteration-loop`); reproducing a supplied design exactly (`pixel-perfect`); static markup/CSS conventions alone (`frontend-markup-practices`); or making an accessibility-conformance claim (`wcag-accessibility-practices`, paired when relevant).

## Workflow

1. **Inspect project truth.** Identify framework, browser support, tokens, component library, typefaces and available weights, reset styles, breakpoints, themes, localization, and existing component patterns. Reuse them before inventing values.
2. **Choose the relevant branch.** Load only the needed reference:
   - `references/typography-and-content.md`
   - `references/forms-and-validation.md`
   - `references/layout-navigation-and-attention.md`
   - `references/visual-system-and-data.md`
   - `references/async-empty-error-and-success.md`
3. **Define the contract.** Record tokens and semantic structure, responsive behavior, interaction states, content extremes, accessibility target, and which source tips are applied, adapted, or rejected.
4. **Implement every applicable state.** Default, hover, focus-visible, active, selected, disabled-with-reason, loading, empty, error, success, narrow/wide, zoom/reflow, reduced motion, long/localized content, keyboard, and assistive semantics.
5. **Render and inspect.** Compare representative viewport/state screenshots. Test actual fonts, strings, values, images, tables, errors, latency, and input methods—not lorem ipsum and the happy path.
6. **Run deterministic gates.** Project tests plus lint/type/build; contrast and semantics tools where applicable; keyboard traversal; 200% zoom and narrow reflow; reduced motion; state and visual regression checks.

## Hard Rules

- Never shrink text or hit targets merely to make content fit.
- Never use placeholder, color, icon, hover, gesture, motion, or toast timing as the only carrier of required meaning.
- Never claim a PDF number is a WCAG requirement.
- Never replace native semantics with a custom control unless the behavior is fully reproduced.
- Never ship only the ideal screenshot; loading, failure, recovery, localization, and real data are part of the component.

## Verification

Report changed components, reused/added tokens, source tips applied/adapted/rejected, rendered states and viewports, keyboard/zoom/motion checks, automated gates, unresolved browser/font/content risks, and before/after evidence.

## References

The five branch files above contain the actionable frontend rules. `references/pdf-coverage-matrix.md` maps every PDF page-level tip to its owning branch and verification hook. `references/sources-and-validation.md` records source values, boundaries, coverage proof, and behavioral probes.
