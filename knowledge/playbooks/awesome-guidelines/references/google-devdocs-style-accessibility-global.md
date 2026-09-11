<!-- capsule-v2 -->
# Accessibility and global audience — is content inclusive, unambiguous, and translation-ready?

**Source:** Google style §Write accessible documentation, §Write for a global audience, §Highlights. **Question:** Do headings, links, images, and wording support screen readers and localization?

## Accessibility seam
**Path/Symbol:** all developer docs; HTML/Markdown output.
**Signature:** semantic headings; alt text; no directional-only cues; short sentences.
**Data Shape:** WCAG-minded contrast; keyboard reachable interactive elements.

### Decisive pattern
```
In the preceding diagram, clients connect to the load balancer.

![Architecture diagram showing client to load balancer flow](diagram.svg)
```

**Flow:** write so content works without color, images, sound, or layout position → use semantic heading hierarchy (don't skip levels for styling) → meaningful link text; use **see** for cross-refs → provide **alt** for images; empty alt if decorative → don't put new information only in images/screenshots → prefer real text over images of code → avoid directional language (above/below/right panel) — use preceding/following → refer to controls by **label**, not icon shape → break up walls of text; ≤26 words per sentence when practical → define acronyms on first use → left-align text → avoid ALL CAPS/camelCase when possible for screen readers → don't use & for and in headings/nav (except UI &) → label form fields; clear error messages → test with screen reader when feasible.
**Invariant:** click-here links, missing alt on informative figures, or above/below-only orientation fails accessibility review.
**Probe:** heading hierarchy validation; alt attribute scan; directional word grep.

## Global/i18n seam
**Flow:** US English; short unambiguous sentences; active SVO → avoid phrasal verbs when simpler verb works → repeat parallel words in lists (then, that, of, articles) for translator clarity → consistent term/capitalization for same concept throughout → avoid idioms, slang, humor, seasonal/cultural-only references → diverse example names → unambiguous dates/times → qualify filenames/commands with nouns (the `example.yaml` file) → conditional clause before instruction → avoid -ing gerund openings when clearer alternative exists.
**Invariant:** synonym swapping for same concept or ambiguous once/since/while in localized doc fails translation readiness review.
**Probe:** terminology consistency grep; ambiguous word checklist from global audience page.

## Verdict
Semantic structure, alt text, non-directional wording, short consistent terms for global readers. Learning note: `google-devdocs-style-learning-note.md`.
