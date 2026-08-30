---
name: google-devdocs-practices
description: "Use when authoring Google-style developer docs, you/imperative voice, sentence-case headings, bold UI and code font, numbered procedures, For more information see links, and accessible global English."
disable-model-invocation: true
---

# Google Developer Documentation Practices

Application skill for Google developer documentation style guide (archived `awesome-guidelines` capsules). For repo Markdown mechanics, load `markdown-writing-practices`. For MDN ``` code blocks, load `mdn-code-examples-practices`. For marketing voice, load `mailchimp-content-practices`.

## Core Principle

Google devdoc quality is **you-focused clarity built for translation**, active conversational prose, sentence-case structure, context-first procedures, descriptive links, consistent terms.

## When to Use / NOT

- API guides, tutorials, concept docs, procedures matching Google developer documentation style.
- Reviewing technical docs before publish on developers.google.com-style sites or internal Google-style portals.

**NOT when:**

- Product marketing landing copy, `mailchimp-content-practices`.
- MDN-specific example code fences, `mdn-code-examples-practices`.
- Non-English source docs, follow locale guide; English rules here are US English baseline.

## Workflow

1. **Voice/person**, you, active, no please (`google-devdocs-style-voice-person.md`).
2. **Format/headings**, sentence case, bold UI, code font (`google-devdocs-style-format-headings.md`).
3. **Procedures/links**, numbered steps, cross-refs (`google-devdocs-style-procedures-links.md`).
4. **Accessibility/global**, alt text, i18n wording (`google-devdocs-style-accessibility-global.md`).
5. **Verify**, heading outline; link text out-of-context test; please/click here grep; term consistency scan.

## Red Flags

- we/our when instructing the reader (should be you)
- please in procedural steps
- Passive voice hiding required reader action
- simply / easy / quickly in instructions
- Exclamation marks in technical content
- Title Case or ALL CAPS headings
- Task heading starting with -ing (Creating…)
- Skipped heading levels for visual styling
- Bold for non-UI emphasis
- & instead of and in prose/headings
- click here / this document / raw URL link text
- Linked punctuation (period inside `<a>`)
- For more information on… (should be about when needed)
- Action before location (Click X in console)
- (Optional) instead of Optional:
- Numbered list for single-step task
- Incomplete intro sentence finished by list items
- Directional above/below/right-hand panel
- Missing alt on informative images
- Inconsistent product/API term for same concept
- Code font on product names or navigation URLs
- Buzzword/jargon without brief definition

## Verification

- Heading hierarchy outline (one h1, no level skips)
- grep `\bplease\b`, `click here`, `this document` in changed prose
- Link text read out of context, still meaningful?
- Acronym first-use expansion check
- Optional: accessibility lint (alt, heading order) on rendered HTML
- Cross-check project-specific style overrides first in reference hierarchy

## Skill Result Contract

```xml
<skill_result>
  <skill>google-devdocs-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>doc diff, review checklist output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>non-you voice, vague links, or heading hierarchy drift</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/google-devdocs-style-learning-note.md`
- `awesome-guidelines/references/google-devdocs-style-voice-person.md`
- `awesome-guidelines/references/google-devdocs-style-format-headings.md`
- `awesome-guidelines/references/google-devdocs-style-procedures-links.md`
- `awesome-guidelines/references/google-devdocs-style-accessibility-global.md`

## Related skills

- `markdown-writing-practices`, repo Markdown layout
- `mdn-code-examples-practices`, MDN code example blocks
- `mailchimp-content-practices`, product/marketing copy voice
