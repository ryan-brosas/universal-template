# WCAG 2.1 accessibility — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `wcag-*.md` capsules, `wcag-accessibility-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [WCAG 2.1 Recommendation](https://www.w3.org/TR/WCAG21/) (primary normative) | Four principles POUR; Level A/AA/AAA; 50 success criteria in 2.1 |
| [How to Meet WCAG (Quick Reference) 2.1](https://www.w3.org/WAI/WCAG21/quickref/?versions=2.1&levels=aa) (primary map) | Principle/guideline/SC hierarchy; AA filter set |
| [Understanding WCAG 2.1](https://www.w3.org/WAI/WCAG21/Understanding/) (primary explanatory) | Intent for 1.1.1, 1.4.3, 1.4.10, 2.1.1, 2.4.7, 3.3.1–2, 4.1.2 |
| [WCAG 2 Overview](https://www.w3.org/WAI/standards-guidelines/wcag/) (secondary) | Conformance scope, relationship of WCAG/Understanding/Techniques |
| `frontend-markup-practices` (secondary) | Semantic HTML baseline — WCAG adds measurable SC + AT requirements |
| `mailchimp-content-practices` / `google-devdocs-practices` (secondary) | Copy/link/heading a11y for content-heavy surfaces |

**Scope:** **Web content conformance** to **WCAG 2.1 Level AA** — success criteria, not full legal procurement (Section 508 mapping out of scope). **Component libraries / SPA:** same SC apply via DOM + ARIA. **Native mobile:** platform HIG; this skill is web-first.

**Default target:** **Level AA** unless product policy states A-only or AAA for specific SC.

## Mental model — POUR

1. **Perceivable (1.x)** — text alternatives, adaptable structure, distinguishable presentation (contrast, resize, reflow).
2. **Operable (2.x)** — keyboard access, enough time, no seizure triggers, navigable focus/skip links, pointer alternatives.
3. **Understandable (3.x)** — readable language, predictable behavior, form labels/errors/suggestions.
4. **Robust (4.x)** — valid name/role/value for AT; status messages programmatically available.

Conformance = satisfy **all Level A + all Level AA** success criteria for the **scope of claim** (page, flow, or site). Techniques are informative; failing a technique does not automatically fail SC if another sufficient technique passes.

## Decision tables

### Perceivable — high-impact AA

| SC | Rule |
|---|---|
| 1.1.1 Non-text Content | Informative images/controls have equivalent text; decorative `alt=""`; CAPTCHA has text alternative |
| 1.3.1 Info and Relationships | Structure programmatically available — headings, labels, lists, tables |
| 1.3.3 Sensory Characteristics | Don't instruct by shape/color/location alone |
| 1.3.4 Orientation (2.1) | Don't lock to portrait/landscape only |
| 1.3.5 Identify Input Purpose (2.1) | Autocomplete tokens on common personal fields |
| 1.4.3 Contrast (Minimum) | 4.5:1 normal text; 3:1 large text (18pt+ or 14pt bold+) |
| 1.4.4 Resize Text | 200% zoom without loss of content/function |
| 1.4.10 Reflow (2.1) | 320px width reflow without two-dimensional scroll for vertical content |
| 1.4.11 Non-text Contrast (2.1) | UI components/graphical objects 3:1 against adjacent colors |
| 1.4.12 Text Spacing (2.1) | User spacing overrides don't break content |
| 1.4.13 Content on Hover/Focus (2.1) | Dismissible, hoverable, persistent tooltips/menus |

### Operable — high-impact AA

| SC | Rule |
|---|---|
| 2.1.1 Keyboard | All functionality via keyboard unless path-dependent input |
| 2.1.2 No Keyboard Trap | Focus can leave every component |
| 2.1.4 Character Key Shortcuts (2.1) | Single-key shortcuts remappable/off with focus |
| 2.2.1 Timing Adjustable | Time limits extendable unless essential |
| 2.2.2 Pause, Stop, Hide | Moving/blinking/auto-updating content controllable |
| 2.3.1 Three Flashes | No content flashes >3 per second |
| 2.4.1 Bypass Blocks | Skip link or landmarks to main content |
| 2.4.2 Page Titled | Descriptive `<title>` |
| 2.4.3 Focus Order | Logical tab order |
| 2.4.4 Link Purpose | Link text meaningful in context |
| 2.4.6 Headings and Labels | Descriptive headings/labels |
| 2.4.7 Focus Visible | Keyboard focus indicator visible |
| 2.5.1 Pointer Gestures (2.1) | Multipoint/path gestures have single-pointer alternative |
| 2.5.2 Pointer Cancellation (2.1) | Up-event activates; abort/down-cancel pattern |
| 2.5.3 Label in Name (2.1) | Visible label in accessible name |
| 2.5.4 Motion Actuation (2.1) | Device motion has UI alternative + disable |

### Understandable — high-impact AA

| SC | Rule |
|---|---|
| 3.1.1 Language of Page | `lang` on `<html>` |
| 3.1.2 Language of Parts | `lang` on foreign phrases |
| 3.2.1 On Focus | No context change on focus alone |
| 3.2.2 On Input | No unexpected context change on input |
| 3.3.1 Error Identification | Errors described in text |
| 3.3.2 Labels or Instructions | Inputs have labels/instructions |
| 3.3.3 Error Suggestion | Fix suggestions when known |
| 3.3.4 Error Prevention (legal/financial) | Reversible/confirmed submissions |

### Robust — AA

| SC | Rule |
|---|---|
| 4.1.1 Parsing (2.1) | No duplicate IDs; complete start/end tags |
| 4.1.2 Name, Role, Value | Custom widgets expose correct accessibility API |
| 4.1.3 Status Messages (2.1) | Status updates available to AT without focus move |

## Anti-patterns

- Missing or filename `alt` on informative images
- Color-only error/state indication (1.4.1 / 1.3.3)
- `<div onclick>` with no keyboard path (2.1.1 / 4.1.2)
- Focus outline removed without replacement (2.4.7 / 1.4.11)
- Placeholder-only “labels” (3.3.2 / 4.1.2)
- Icon button without accessible name
- Auto-advancing carousel with no pause (2.2.2)
- Modal without focus trap management + escape (2.1.2 / 2.4.3)
- `lang` missing on mixed-language page (3.1.1)
- Form submit changes context without warning (3.2.2)
- “Click here” links (2.4.4)
- Custom select without role/state (4.1.2)
- Toast success only visual — no live region (4.1.3)
- Claiming AAA while only testing happy-path keyboard once
- Relying on automated axe pass alone for full AA claim

## Skill trace

| Artifact | Role |
|---|---|
| `wcag-perceivable-media-text.md` | Principle 1 AA |
| `wcag-operable-keyboard-focus.md` | Principle 2 AA |
| `wcag-understandable-forms-language.md` | Principle 3 AA |
| `wcag-robust-verify.md` | Principle 4 AA + verification |
| `wcag-accessibility-practices/SKILL.md` | conformance review workflow |

## Relation to sibling skills

| WCAG skill | frontend-markup-practices |
|---|---|
| Normative SC checklist | HTML/CSS authoring conventions |
| Keyboard/focus/ARIA requirements | Semantic element choice |
| Measurable contrast/reflow | Asset delivery + validator |
| Applies to SPAs/components | Static template focus |

Copy-heavy docs: also `mailchimp-content-practices`, `google-devdocs-practices`.
