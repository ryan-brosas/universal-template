# PDF Tip-to-Test Crosswalk

Use this after identifying a task break. The book’s examples are inspection prompts, not compliance rules. Each group below converts every contents-page tip into an observable question. Apply only relevant rows; current WCAG, platform conventions, project evidence, security, and the design system outrank the PDF’s informal numbers.

## Typography

| Source tip | Testable question |
|---|---|
| Headings close to paragraphs | Can people correctly group each heading with its content at a glance? |
| Avoid justification | Do spacing rivers or dyslexia-related reading difficulties appear with real text and zoom? |
| Make text scannable | Can users locate the needed fact without reading linearly? |
| Links look like links | Are links identifiable without hover, color-only cues, or prior knowledge? |
| Proper line height / line length | Can users track lines comfortably across viewport, font, zoom, and language changes? |
| Multiple hierarchy techniques / do not over-emphasize | Is hierarchy clear without making everything compete? |
| Contrast | Does text meet the project’s WCAG target and remain readable in context? |
| Avoid pure black | Treat as an aesthetic hypothesis; test readability and preference rather than banning `#000`. |
| Text on images | Does contrast survive every crop and image, without obscuring meaningful content? |
| Modular type scale | Does the scale create coherent hierarchy across real components? |
| Tabular figures | Do changing numbers and columns remain aligned and scannable? |

## Forms and validation

| Source tip | Testable question |
|---|---|
| Input spacing | Is each label, hint, error, and control perceptually grouped? |
| Visible tips / password rules | Is prerequisite guidance present before the error can occur? |
| Avoid multicolumn forms | Does visual and keyboard order stay unambiguous; are inline fields truly one compound value? |
| Labels, not placeholders | Does field purpose remain visible after entry, autofill, error, and speech input? |
| Dropdown caution | Is selection actually easier than direct entry or exposed options for this set? |
| Custom file input | Preserve native semantics while adding useful preview, validation, progress, cancel, and retry. |
| Autofocus | Does it help desktop flow without stealing focus, context, or opening a mobile keyboard unexpectedly? |
| Input width | Does width communicate expected content without harming responsive layout? |
| Preserve failed-login values / remembered reset email | Can users correct and continue without re-entering known data, subject to privacy and security? |
| Multiple steps | Does reduced per-step effort outweigh extra navigation, uncertainty, and recovery cost? |
| Correct input type | Do mobile keyboard, autocomplete, validation, and assistive semantics match the data? |
| Required/optional marking | Can users determine requirements per field without remembering global instructions? |
| Progressive disclosure | Are rare controls deferred without hiding prerequisites or current state? |
| Collapsed filters | Is applied-filter state obvious while options remain discoverable? |
| Scroll/focus first error | Can users perceive the transition, land at the error, and recover with keyboard or assistive tech? |
| Prevent mistakes / positive feedback / inline errors | Is feedback timely, specific, non-noisy, announced, and attached to the responsible field? |

## Landing pages and content

| Source tip | Testable question |
|---|---|
| Fewer fields | Does each field earn its effort and commitment level? |
| Hero contrast / limited copy / text width / font size | Can target users understand the proposition and act at representative sizes and crops? |
| Block separation / false bottom / scroll hint | Is continuation and section structure perceivable without decorative ambiguity? |
| Product illustration | Does imagery explain actual value or workflow rather than merely decorate? |

## Usability and interaction

| Source tip | Testable question |
|---|---|
| Expected placement | Does first-click behavior match the audience’s learned conventions? |
| Delay welcome email on mobile | Is the message timed to be useful rather than interrupting the active task? |
| Labels above sliders | Can values and meaning be read without being covered by the hand or pointer? |
| Verification code notification/SMS and instant checking | Can users transfer or autofill the code with minimal context switching and clear failure recovery? |
| Separate dangerous and frequent actions | Do motor slips avoid irreversible harm? |
| Frequent options first | Does ordering reduce search cost without hiding a user’s likely choice? |
| Avoid carousels | If used, can content be discovered, controlled, paused, navigated, and understood accessibly? |
| Undo versus confirmation | Match prevention to severity and reversibility; does recovery actually restore state? |
| Label icons | Can unfamiliar actions be understood without tooltip-only access? |
| Further instructions | Are next steps available at the moment of uncertainty? |
| Password reveal target | Can users toggle visibility without accidentally editing or submitting? |

## Visual semantics and data

| Source tip | Testable question |
|---|---|
| Animation speed | Does motion explain continuity without delaying work or violating reduced-motion preferences? |
| Normalize charts | Are axes, scales, baselines, and units comparable without distortion? |
| Country flags | Does the symbol represent language/locale accurately for the audience? |
| Map detail | Is visual detail proportional to the decision being made? |
| Buttons versus tags | Does styling communicate action, selection, metadata, and status distinctly? |
| Icon sizing and consistency | Do optical size, stroke, family, and meaning remain coherent? |
| Modal depth / shadows | Is layering and current interaction context clear? |
| Overlap | Does intentional overlap imply the right grouping without hiding content? |
| Similarity / pie grouping / logical grouping | Do perceptual groups match the data and task? |
| Images | Are crop, aspect ratio, quality, meaning, and alternatives robust? |
| Primary-color restraint | Does priority remain legible when many components compete? |
| Dark-mode saturation / table borders | Is contrast sufficient without glare or visual noise? |

## Loading, empty, focus, navigation, and edge cases

| Source tip | Testable question |
|---|---|
| Useful empty state | Does it explain why, what can happen next, and how to recover? |
| Prevent layout and loading-button shifts | Does geometry remain stable and focus stay predictable? |
| Loader placement and delay | Is feedback attached to the changing region and timed to avoid both flicker and silent waiting? |
| Progressive loader | Does feedback communicate useful progress without pretending certainty? |
| De-emphasis / search highlighting | Does attention support the current task without hiding context or relying on color alone? |
| Brief notifications / one hint / one primary dialog action | Can users notice, understand, dismiss, and later recover durable details? |
| Faces and pointing cues | Treat as an attention hypothesis; verify it helps rather than manipulates or distracts. |
| Visible navigation / orientation / active link / breadcrumbs | Can users predict destination, know location, and recover from a wrong turn? |
| Larger targets | Do pointer, touch, keyboard, switch, and voice users activate the intended control? |
| Vertical/horizontal/fluid/fixed navigation / overflow links | Does navigation survive content growth, zoom, localization, and narrow viewports? |
| Color blindness plus icons | Is meaning redundant across color, text, shape, and semantics? |
| Decorative alt text | Is decoration ignored while informative imagery gets equivalent purpose? |
| Baseline alignment | Does optical alignment remain coherent across mixed content and fonts? |
| Rating vote count | Are denominator, sample size, and uncertainty visible enough to interpret the score? |
| Result counts and filter indicators | Can users predict filter impact and see the active query state? |
| Responsive tables | Are task-critical comparisons preserved, labeled, and operable on narrow screens? |
| Post date | Is freshness visible where age changes credibility or action? |
| Large data | Do overflow, wrapping, truncation, precision, localization, and extreme values remain usable? |

## Coverage rule

A PDF row is “considered” only when the task makes it relevant and the decision ledger records **apply**, **adapt**, or **reject**, with the reason. Checklist completion is not evidence of improved UX.
