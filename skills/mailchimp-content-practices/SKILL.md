---
name: mailchimp-content-practices
description: "Use when authoring or reviewing product/marketing copy, Mailchimp plainspoken voice, active positive language, inclusive people terms, sentence-case UI headings, descriptive links, a11y, and translation-safe SVO."
invocation: manual
disable-model-invocation: true
---

# Mailchimp Content Practices

Application skill for Mailchimp Content Style Guide (archived `awesome-guidelines` capsules). For repo Markdown structure (H1, fences, wrap), load `markdown-writing-practices` first; apply this skill to user-facing voice, UI microcopy, and inclusive language.

## Core Principle

Product copy quality is **clear, person-first, and scannable**, plainspoken voice, active positive sentences, inclusive terms, descriptive links, and translation-safe structure.

## When to Use / NOT

- Marketing pages, in-app UI strings, help center, emails, forms, error messages, blog/product copy.
- Reviewing copy for voice, inclusivity, link text, heading hierarchy, localization.

**NOT when:**

- Internal repo docs where only Markdown mechanics matter, `markdown-writing-practices`.
- API/code identifiers, stack naming skills.
- Legal contracts requiring non-Mailchimp house style, follow legal template.

## Workflow

1. **Voice/tone**, plainspoken, active, positive (`mailchimp-style-voice-tone.md`).
2. **Grammar/structure**, hierarchy, numbers, punctuation (`mailchimp-style-grammar-structure.md`).
3. **Inclusive people**, they/them, bias-free terms (`mailchimp-style-inclusive-people.md`).
4. **Web/a11y/i18n**, headings, links, forms, translation (`mailchimp-style-web-accessibility-i18n.md`).
5. **Verify**, read aloud; heading outline; link/descriptive text scan; word-list grep for banned terms.

## Red Flags

- Passive voice by default
- Jargon without brief definition
- Negative framing when positive works
- “Click here” / “Learn more” link anchors
- Directional copy (“panel on the right”)
- Skipped heading levels for styling
- Title case on body headings when sentence case required
- Buttons without verbs
- Forms asking irrelevant personal data (e.g. gender dropdown)
- Missing or decorative-only alt text on informative images
- Exclamation points in failure/error messages
- “Guys”, ninja/rockstar/wizard, master/slave, blacklist/whitelist
- Age terms (young/old/elderly) when irrelevant
- Ambiguous once/since/right in localized strings
- `-ing` heavy translation-bound sentences
- `$25` instead of `25 USD` for international content
- Keyword stuffing for SEO
- Writing in mascot/character voice
- Underline or bold+italic+caps emphasis stacks

## Verification

- Read-aloud pass for awkward or passive sentences
- Heading hierarchy outline (H1→H2→H3, no skips)
- Link text audit (meaningful anchors, no linked punctuation)
- grep banned terms from word list (`blacklist`, `guys`, `automagical`, etc.)
- For localized strings: translation checklist (SVO, repeated parallel verbs, ambiguity scan)
- Optional: accessibility review (alt text, form labels, no direction-only instructions)


## References

- `awesome-guidelines/references/mailchimp-style-learning-note.md`
- `awesome-guidelines/references/mailchimp-style-voice-tone.md`
- `awesome-guidelines/references/mailchimp-style-grammar-structure.md`
- `awesome-guidelines/references/mailchimp-style-inclusive-people.md`
- `awesome-guidelines/references/mailchimp-style-web-accessibility-i18n.md`

## Related skills

- `markdown-writing-practices`, repo Markdown layout and fences
- `frontend-markup-practices`, semantic HTML when copy ships in templates
