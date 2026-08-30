# Google developer documentation style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `google-devdocs-style-*.md` capsules, `google-devdocs-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google developer documentation style guide](https://developers.google.com/style) (primary hub) | Project style → this guide → Merriam-Webster/Chicago/Microsoft; clarity over rigid rules |
| [Highlights](https://developers.google.com/style/highlights) (primary) | Conversational; second person; active voice; sentence-case headings; serial comma; descriptive links; alt text |
| [Voice and tone](https://developers.google.com/style/tone) (primary) | Friendly not frivolous; global audience; avoid buzzwords, please note, simply/easy, exclamation marks |
| [Second person and first person](https://developers.google.com/style/person) (primary) | you/your not we; imperative instructions; third person for software facts |
| [Active voice](https://developers.google.com/style/voice) (primary) | Active default; passive OK for emphasis/de-emphasis/irrelevant actor |
| [Text-formatting summary](https://developers.google.com/style/text-formatting) (primary) | Bold UI only; italics sparingly; code font; sentence case headings; no & in prose |
| [Headings and titles](https://developers.google.com/style/headings) (primary) | Task bare infinitive; concept noun phrase; no -ing first word; hierarchy; Optional: prefix |
| [Lists](https://developers.google.com/style/lists) (primary) | Numbered sequences; bullets otherwise; description lists; complete intro sentence |
| [Cross-references and linking](https://developers.google.com/style/link-text) (primary) | Descriptive links; For more information, see/about; no click here; punctuation outside links |
| [Procedures](https://developers.google.com/style/procedures) (primary) | Numbered steps; context before action; Optional:; location before action; no please |
| [Write accessible documentation](https://developers.google.com/style/accessibility) (primary) | Semantic HTML; alt text; no directional language; short sentences; heading hierarchy |
| [Write for a global audience](https://developers.google.com/style/translation) (primary) | US English; short sentences; avoid phrasal verbs; helper words; consistent terms |
| [Code in text](https://developers.google.com/style/code-in-text) (secondary) | Backticks for filenames, methods, flags, placeholders; not URLs/product names |
| `markdown-writing-practices` / `mailchimp-content-practices` (secondary) | Repo MD vs product marketing voice — Google guide is **developer technical docs** |

**Scope:** **Google-style developer documentation** (API refs, guides, tutorials). **MDN example code:** `mdn-code-examples-practices`. **Marketing copy:** `mailchimp-content-practices`.

## Mental model

Google devdocs quality is **clear, you-focused, translation-ready technical prose**:

1. **Voice/person** — conversational; address reader as you; active voice; imperative steps; no please in instructions.
2. **Format/headings** — sentence case everywhere; bold UI; code font for code tokens; serial comma; UI before action in steps.
3. **Procedures/links** — numbered procedures; complete list intros; descriptive link text; For more information, see…
4. **Accessibility/global** — heading hierarchy; alt text; no above/below; short sentences; consistent terminology; inclusive examples.

## Decision tables

### Voice, tone, person

| Topic | Rule |
|---|---|
| Tone | conversational, friendly, respectful; not frivolous or overly formal |
| Audience | developers; identify reader role early |
| Person | second person you/your for tasks; we/our only for org as author when clear |
| Instructions | imperative (Click Submit) — no please |
| Active voice | default; passive when object emphasized or actor irrelevant |
| Avoid | buzzwords, simply/easy/quickly, let's, exclamation marks, pop culture, ableist figurative language |
| Global | avoid culturally specific references; simple consistent sentences |

### Headings & formatting

| Topic | Rule |
|---|---|
| Case | sentence case all headings/titles/nav |
| Task headings | bare infinitive (Create an instance) |
| Concept headings | noun phrase; avoid leading -ing |
| Optional sections | `Optional:` prefix in heading |
| Hierarchy | one h1 per page; don't skip levels; no empty headings |
| Bold | UI elements and notice run-in headings only |
| Italics | terms as words; emphasis sparingly; not bold+underline stacks |
| Code font | filenames, methods, flags, placeholders, HTTP codes in prose |
| Underline | links only |
| Ampersand | and not & (except UI labels that use &) |

### Lists & procedures

| Topic | Rule |
|---|---|
| Numbered | sequences, procedures |
| Bulleted | non-sequential sets |
| Description lists | term + definition pairs |
| Intro | complete sentence before list (colon if list follows immediately) |
| Single-step | one bullet sentence, not numbered "1." |
| Sub-steps | lowercase letters; roman numerals nested |
| Context | location/tool before action (In the console, click…) |
| Goal | To VERB, click… (or Goal: click…) |
| Optional step | `Optional:` at step start |
| Multi-action | File > New > Document in one step when small |
| Conditions | before instructions, not after |

### Linking

| Topic | Rule |
|---|---|
| Text | page title or descriptive phrase; meaningful out of context |
| Avoid | click here, this document, raw URLs as text |
| Intro | For more information, see/about… (about when purpose unclear) |
| Punctuation | outside link tags |
| Behavior | same tab default; explain downloads/new tab |
| Duplicates | one primary link per destination per page |

### Accessibility & i18n

| Topic | Rule |
|---|---|
| Headings | unique, hierarchical, semantic tags |
| Links | meaningful; see for cross-refs |
| Images | alt text; no new info only in images; prefer text over image-of-text |
| Direction | preceding/following not above/below |
| Sentences | ≤26 words when possible; define acronyms |
| Terms | consistent naming/capitalization throughout |
| Translation | repeat parallel words; helper words (then, that); avoid phrasal verbs |
| Inclusive | diverse example names; unambiguous dates |

## Anti-patterns

- we/our when you/your is meant for the reader
- please in procedural steps
- click here / read this document link text
- sentence case violated (Title Case headings)
- -ing as first word of task heading (Creating…)
- Skipped heading levels for styling
- Bold for emphasis (non-UI)
- & instead of and in headings/prose
- Directional above/below/right-hand panel
- simply / It's easy / quickly in procedures
- Exclamation marks in technical docs
- Partial intro sentence completed by list items
- Numbered list for single step
- (Optional) instead of Optional:
- Putting action before location (Click X in Console → prefer In Console, click X)
- Inconsistent term for same concept across doc
- Code font on product names or bare URLs
- Hard line breaks inside sentences
- Tables for simple lists; lists for multi-property data (wrong container)

## Skill trace

| Artifact | Role |
|---|---|
| `google-devdocs-style-voice-person.md` | tone, you, active voice, avoid please |
| `google-devdocs-style-format-headings.md` | sentence case, bold/code, lists intro |
| `google-devdocs-style-procedures-links.md` | steps, links, cross-refs |
| `google-devdocs-style-accessibility-global.md` | a11y, i18n, inclusive, terms |
| `google-devdocs-practices/SKILL.md` | Google-style devdoc review workflow |

## Reference hierarchy (Google)

1. Project-specific style (if any)
2. [developers.google.com/style](https://developers.google.com/style)
3. Merriam-Webster (spelling), Chicago (nontechnical), Microsoft Writing Style Guide (technical, with product filter)

## Relation to sibling skills

| Google devdocs | Mailchimp | MDN examples | Markdown |
|---|---|---|---|
| you-focused dev tutorials | product/marketing voice | ``` code blocks in articles | repo MD structure |
| bold UI elements | title/sentence case UI tables | Prettier on code | H1/fences |
| For more information, see | descriptive links | descriptive links | reference links |
| Procedures numbered | web forms/nav case | JS/HTML/CSS example rules | 80-col wrap |
