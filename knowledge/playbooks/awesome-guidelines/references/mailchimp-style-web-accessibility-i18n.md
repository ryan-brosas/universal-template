<!-- capsule-v2 -->
# Web, accessibility, and i18n — do UI copy, links, and structure work for all readers and locales?

**Source:** Mailchimp Content Style Guide §Web Elements, §Writing for Accessibility, §Writing for Translation. **Question:** Are headings, buttons, links, forms, alt text, and translation-bound strings built for scan, assistive tech, and translators?

## Web structure seam
**Path/Symbol:** pages, forms, nav, buttons, headings in product UI and web content.
**Signature:** one topic per page; sentence-case headings; title-case page titles; verb buttons.
**Data Shape:** H1 page title → H2 sections → H3 subsections without level skips.

### Decisive pattern
```
Title: Create a Campaign        (title case)
H2: Choose your audience        (sentence case)
Button: Save and continue       (sentence case, verb-led)
Link: Read the automation guide (descriptive anchor)
```

**Flow:** organize each page around one topic → page **titles** in title case without trailing period unless question → **headings/subheadings** in sentence case with logical H1→H2→H3 hierarchy and relevant keywords → buttons include verbs; sentence case; concise (“Log in”, “Email us”) → checkboxes/radio in sentence case → drop-down: title case name, sentence case items → forms: title case title, sentence case fields; collect only needed data; avoid irrelevant gender — free-text if required → main nav title case; subnav sentence case → lists: brief intro; numbered when order matters → SEO: human-first; descriptive headings; no keyword stuffing.
**Invariant:** “Click here” links, skipped heading levels, or verb-less buttons fail web copy review.
**Probe:** link text audit; heading outline scan; form field necessity review.

## Accessibility seam
**Flow:** avoid directional instructions (“right sidebar”) → nest headings consecutively → most important information first; separate topics with headings → use true lists, not paragraph line breaks → link text describes action/destination (not “learn more”) → alt text on all images — functional images described for equivalent information → don’t rely on color/image alone → label form inputs clearly; mark required fields; keep forms short → captions/transcripts for video when applicable.
**Invariant:** layout-dependent or empty alt text on informative images fails accessibility review.
**Probe:** screen-reader pass: does copy make sense without layout/color?

## Translation seam
**Flow:** prefer active subject-verb-object → repeat verbs/subjects/markers in parallel constructions for clarity → keep `then`, articles, and `that` when they disambiguate → avoid `-ing` forms when rewritable → avoid slang, idioms, cliches, e.g./i.e., and synonym swapping for the same concept → avoid ambiguous once/since/right/require/have+participle → use metric units spelled out; currency as `25 USD` not `$25` → translation-bound sections override brevity hacks that harm clarity.
**Invariant:** ambiguous pronoun reference or `-ing` heavy string slated for localization fails i18n review.
**Probe:** mark strings for translation review; apply repetition/ambiguity checklist.

## Verdict
Descriptive links, nested headings, minimal forms, alt text, translation-safe SVO and explicit parallel verbs. Learning note: `mailchimp-style-learning-note.md`.
