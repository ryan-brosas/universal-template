<!-- capsule-v2 -->
# Format and headings — are sentence case, UI bold, and code font applied correctly?

**Source:** Google style §Text-formatting summary, §Headings and titles, §Lists (intros). **Question:** Do headings follow task/concept patterns with proper hierarchy and typography rules?

## Heading seam
**Path/Symbol:** page titles, section headings, nav labels.
**Signature:** sentence case; one h1; task bare infinitive; concept noun phrase.
**Data Shape:** Optional: prefix; no skipped levels.

### Decisive pattern
```markdown
# Create a VM instance

## Configure network settings

### Optional: Enable custom hostname
```

**Flow:** use **sentence case** for all headings, titles, navigation → one unique level-1 heading per page → task sections: bare infinitive heading (Create an instance) → conceptual sections: noun phrase without leading -ing (Migration to Cloud) → optional sections: `Optional:` prefix at start → avoid -ing as first heading word when rewrite possible → don't skip heading levels; no empty headings → don't put links inside headings → introduce groups of subsections with "the following sections" → lists: precede with **complete intro sentence** (colon if list immediately follows); don't let list finish a fragment sentence.
**Invariant:** Title Case headings, Creating… task titles, or h3 without h2 fails Google heading review.
**Probe:** heading outline; case scan; -ing first-word check on task pages.

## Typography seam
**Flow:** **bold** (`**` in Markdown) for UI elements and notice run-in headings only → *italics* sparingly for terms/emphasis; `_` preferred over `*` in Markdown for italics → `code font` for filenames, methods, flags, placeholders, HTTP codes, element names in prose → underline reserved for links → serial comma → don't use & for and in prose/headings (OK in UI names that contain &) → left-align body text; no inline font overrides.
**Invariant:** bold for generic emphasis or code font on product names/URLs fails formatting review.
**Probe:** spot UI labels for bold; grep backticks on technical tokens.

## Verdict
Sentence-case hierarchical headings, bold UI, code font for code tokens, complete list intros. Learning note: `google-devdocs-style-learning-note.md`.
