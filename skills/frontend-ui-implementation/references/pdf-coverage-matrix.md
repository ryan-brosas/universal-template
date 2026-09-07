# Complete PDF Coverage Matrix

Source: Victor Ponamariov, *100 Practical UI/UX Tips*, pages 8–107. This matrix prevents tips from disappearing into abstraction. Each of the 100 numbered tip pages has one frontend owner and a concrete verification hook. Values copied from the PDF are source defaults, not WCAG requirements.

Owners: **T** typography/content, **F** forms/validation, **L** layout/navigation/attention, **V** visual system/data, **A** async/empty/error/success.

## Typography, forms, and validation

| Page | Source tip | Owner | Implementation and verification hook |
|---:|---|:---:|---|
| 8 | Place headings close to their paragraphs | T | Flow-space token: heading-to-owned-content < preceding-section gap; inspect wrapping/breakpoints. |
| 9 | Avoid text justification | T | `text-align:start` for prose; inspect spacing rivers, zoom, narrow width, and dyslexia-sensitive readability. |
| 10 | Make text easy to scan | T | Semantic headings, real lists, concise blocks; run a locate-the-fact task. |
| 11 | Make links look like links | T | Non-hover, noncolor affordance plus focus-visible; inspect body copy in both themes. |
| 12 | Use proper line height | T | Preserve PDF bands: heading 1–1.4, body 1.3–1.6 as starting ranges; test glyph clipping and wraps. |
| 13 | Do not make lines too lengthy | T | Preserve PDF 45–75ch / cited 50–60ch guidance; inspect actual font/language at narrow and wide sizes. |
| 14 | Use different hierarchy techniques | T | Coordinate size, weight, color, position, spacing, type contrast; verify hierarchy without size alone. |
| 15 | Do not over-emphasize | T | Remove redundant emphasis signals; confirm one clear reading order. |
| 16 | Keep an eye on contrast | T | Test text/UI contrast against project WCAG target and rendered readability; passing ratio alone is not readability proof. |
| 17 | Do not use pure black color | T | Compare pure/near-black in context; do not encode PDF preference as a ban. |
| 18 | Handle text on images properly | T | Test tint/box/blur/fade across every image crop and breakpoint. |
| 19 | Use modular type scale | T | Preserve PDF examples: 16px base; ratios 1.25, 1.414, 1.5; adapt to project tokens and small screens. |
| 20 | Proportional vs tabular figures | T | Apply tabular numerals to changing/aligned columns; inspect font support and alignment. |
| 21 | Have enough space between inputs | F | Within-field gap < between-field gap; inspect label/hint/error ownership. |
| 22 | Do not hide form tips | F | Required guidance persistent and associated; tooltip only supplemental. |
| 23 | Show password rules right away | F | Rules visible before submission; update satisfied state without color-only meaning. |
| 24 | Avoid multicolumn layouts | F | One DOM/visual sequence; inline only true compound values; verify tab and error order. |
| 25 | Use labels, not placeholders | F | Persistent semantic labels survive typing, autofill, and errors. |
| 26 | Be careful with dropdowns | F | Preserve PDF 5–7 heuristic as a prompt; choose radios, direct input, select, or searchable combobox from task/data. |
| 27 | Replace default file inputs | F | Retain native semantics while adding preview, progress, validation, cancel, and retry. |
| 28 | Autofocus the first input | F | Apply only when context-safe; test mobile keyboard, focus theft, back navigation, and screen reader. |
| 29 | Use reasonable input width | F | Width reflects expected data but reflows; do not use width as validation. |
| 30 | Do not erase credentials after unsuccessful login | F | Preserve correctable values per security contract; test reveal, retry, and server rejection. |
| 31 | Remember email in forgot password page | F | Carry known email across the flow when accurate, expected, editable, and privacy-safe. |
| 32 | Divide form into multiple steps | F | Remove fields first; balance step count and complexity; preserve/back/resume state. |
| 33 | Use correct input type | F | Verify `type`, `inputmode`, autocomplete, keyboard, parser, and semantics. |
| 34 | Mark required/optional fields | F | Status visible per field and programmatically exposed; no remembered top instruction. |
| 35 | Progressive disclosure | F | Hide rare controls, not prerequisites/current state; preserve expansion and focus. |
| 36 | Collapse long checkbox lists | F | Collapsible filters show applied count/state and remain keyboard operable. |
| 37 | Autoscroll to the first error | F | Focus/scroll predictably, account for sticky UI and reduced motion, announce summary/error. |
| 38 | Help users fill forms without mistakes | F | Constraints/examples/available values prevent errors before validation. |
| 39 | Consider positive feedback | F | Confirm genuinely difficult input without announcing noise on every field. |
| 40 | Put error messages in the right place | F | Inline association plus summary when needed; preserve data and next action. |

## Landing pages, interaction, and navigation

| Page | Source tip | Owner | Implementation and verification hook |
|---:|---|:---:|---|
| 41 | Require fewer fields | F | Every field must earn effort/commitment; test completion and data necessity. |
| 42 | Watch text contrast on hero images | T | Verify every source/crop/theme with stable contrast treatment. |
| 43 | Do not have too much text | T | Make feature copy scannable; do not solve density with tiny text. |
| 44 | Wrong blocks separation | L | Common-region/proximity must bind heading and content across breakpoints. |
| 45 | Illustrating your app | V | Crop/enlarge the real feature without fabricating capability; provide meaningful alt/context. |
| 46 | Text container width | T | Constrain heading/subheading measure independently of full-width cards. |
| 47 | False bottom effect | L | Inspect hero/whitespace/footer-like bands and viewport endings for false completion. |
| 48 | Visual hint for scrolling below fold | L | Reveal meaningful next-section content when needed; avoid instruction-only arrows. |
| 49 | Small font size | T | Use a readable base and appropriately large landing display/body scale; test small screens and zoom. |
| 50 | Place inputs where users expect them | L | Follow audience/platform conventions unless task evidence supports deviation. |
| 51 | Delay welcome email on mobile | L | Coordinate channel timing; do not interrupt active task with nonessential message. |
| 52 | Place labels above sliders | L | Keep value visible outside finger occlusion and expose semantic current value. |
| 53 | Verification code push/SMS | F | Put code/purpose in safe notification preview and support OS autofill. |
| 54 | Separate dangerous and frequent actions | L | Spatial/visual separation; test slips, keyboard sequence, undo/confirmation. |
| 55 | False bottom in dropdowns | L | Show overflow/continuation and usable menu height; do not depend on visible scrollbar. |
| 56 | Put frequent options first | L | Order from trustworthy task evidence; preserve all options and personalization control. |
| 57 | Avoid carousels | L | Prefer static content; if retained, test discovery, pause, controls, order, touch, keyboard, and announcements. |
| 58 | Allow undo instead of confirmation | L | Match undo window and confirmation to real reversibility/severity; verify restore. |
| 59 | Label your icons | L | Persistent labels for unfamiliar actions; tooltip/accessibility name alone is insufficient. |
| 60 | Instantly check verification code | F | Auto-submit only on complete unambiguous code with safe retry and announced status. |
| 61 | Provide further instructions | A | Every error/404/onboarding state has a relevant next or recovery action. |
| 62 | Separate area for password toggle | F | Stable nonoverlapping button; password-manager compatibility, pressed state, cursor preservation. |

## Visual system and asynchronous states

| Page | Source tip | Owner | Implementation and verification hook |
|---:|---|:---:|---|
| 63 | Animation speed | V | Preserve PDF bands (<100ms, 100–200ms, 200–300ms, >300ms) as hypotheses; test purpose, perceived latency, reduced motion. |
| 64 | Normalize charts | V | Truthful baseline/domain/units with modest headroom; verify against raw data. |
| 65 | Label country flags | V | Pair with country/language text; never make flag the only identifier. |
| 66 | Low-detail vs high-detail map | V | Ship only task-required detail; verify labels/precision and payload. |
| 67 | Buttons/tags confusion | V | Distinct semantic roles, affordances, selected state, and visual treatments. |
| 68 | Style differently sized icons | V | Normalize optical wrapper/box while preserving hit target and meaning. |
| 69 | Modal depth | V | Elevation token plus real modality, focus trap/return, escape, inert background. |
| 70 | Overlapping trick | L | Decorative overlap cannot obscure, clip, reorder, or imply false relation. |
| 71 | Similarity law | V | Similar appearance only where semantic grouping matches; inspect shape/color/size consistency. |
| 72 | Group pie-chart sections | V | Preserve PDF 5–6 slice suggestion as heuristic; choose chart by task and disclose “Other.” |
| 73 | Styling user images | V | Stable aspect/crop/fallback and subtle inset edge treatment across arbitrary uploads. |
| 74 | Overusing primary color | V | One dominant action per context; implement secondary/tertiary/destructive roles. |
| 75 | Color saturation in dark mode | V | Test vibration, contrast, and hierarchy; do not hard-code a palette family as universal. |
| 76 | Harsh colored table borders | V | Whitespace for sparse tables; subtle rules/striping for dense ones; verify row tracking. |
| 77 | Watch your shadows | V | Shared elevation scale; avoid redundant border+shadow noise; inspect both themes. |
| 78 | Icon consistency | V | Audit family, stroke, fill, optical size, color, complexity, and baseline. |
| 79 | Leverage empty states | A | Distinguish first-use, filtered, permission, failure, and true-empty; provide correct action. |
| 80 | Avoid vertical layout shifts | A | Reserve content geometry/skeleton; measure layout stability under throttling. |
| 81 | Keep button width while loading | A | Reserve label width/min-size; test long localization and accessible loading name. |
| 82 | Correct loader placement | A | Attach to changing region/viewport; ensure visible position and correct blocking semantics. |
| 83 | Do not show loader right away | A | Prevent flicker using measured latency; never turn the PDF’s ~0.5s example into a universal delay. |
| 84 | Use smart/progressive loaders | A | Show truthful long-wait status/cancel/recovery; never fake progress or “almost done.” |

## Attention, navigation, accessibility, and data extremes

| Page | Source tip | Owner | Implementation and verification hook |
|---:|---|:---:|---|
| 85 | De-emphasize other elements | L | Reduce competing salience before increasing target weight; preserve contrast and context. |
| 86 | Highlight search focus | L | Overlay only if useful; no focus trap, hidden navigation, motion, or obscured results. |
| 87 | Do not put too much text in notifications | A | Concise status plus durable detail/history; verify timeout and dismissal. |
| 88 | Do not show multiple hints at once | A | Queue/consolidate ordinary hints while never suppressing critical warnings. |
| 89 | One primary button in dialogs | L | Single dominant task action; other roles distinct and keyboard order logical. |
| 90 | Use face/fingers to direct attention | L | Treat gaze/pointing as optional hypothesis; test distraction, manipulation, and responsive crop. |
| 91 | Do not hide navigation links | L | Keep desktop primary navigation visible when feasible; test discoverability if collapsed. |
| 92 | Increase clickable area | L | Padding expands actual semantic target; verify spacing and WCAG/project target criterion. |
| 93 | Vertical vs horizontal navigation | L | Choose from depth/count/space/frequency; test content growth and narrow width. |
| 94 | More links in horizontal navigation | L | Do not shrink font; restructure or use disclosed overflow while preserving priority/access. |
| 95 | Breadcrumbs pattern | L | Semantic hierarchy, real destinations, current page, keyboard/touch dropdown support if added. |
| 96 | Show active link | L | Current location visible and programmatic (`aria-current` where appropriate), not color-only. |
| 97 | Fluid vs fixed sidebar | L | Content/token-bounded sidebar; test wide screen, zoom, long labels, and resize. |
| 98 | Color blindness and icons | V | Redundant text/shape/icon/semantics; contrast and color-vision checks. |
| 99 | Empty alt for decorative images | V | `alt=""` for truly decorative `<img>`; meaningful images get equivalent purpose. |
| 100 | Align items using baseline | T | Use baseline for text-bearing rows where optical result is correct; inspect mixed fonts/icons. |
| 101 | Show vote count with rating | V | Display denominator and relevant distribution/recency/source; verify aggregation. |
| 102 | Instantly show result count | V | Debounced, race-safe preview with loading/announcement; prevent stale count. |
| 103 | Filters indicator | V | Visible text/count and programmatic state, not only red dot; clear/inspect actions. |
| 104 | Make tables responsive | V | Preserve task via priority columns, named scrolling, compact comparison, or labeled cards. |
| 105 | Group elements logically | L | Group by meaning and whitespace; explicitly reject literal 7±2 item limits. |
| 106 | Put the post date | T | Show published/updated date where freshness changes trust; use semantic machine-readable time. |
| 107 | Remember data can be large | T | Test long/localized/unbroken/huge data; safe wrap/truncate/reveal and server limits. |

Page 108 is the afterward rather than one of the 100 tips. Its controlling rule is retained: every rule has context and exceptions; research, implement, inspect, and iterate.

## Mechanical coverage check

The identifiers `8` through `107` must each occur exactly once in the first column of a coverage row. Run:

```bash
python3 - <<'PY'
import re
from pathlib import Path
text = Path('skills/frontend-ui-implementation/references/pdf-coverage-matrix.md').read_text()
pages = [int(x) for x in re.findall(r'^\| (\d+) \|', text, re.M)]
assert pages == list(range(8, 108)), (len(pages), sorted(set(range(8,108)) - set(pages)))
print('PDF COVERAGE: 100/100')
PY
```
