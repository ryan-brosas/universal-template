# House style rules (detailed)

Explanatory reference for `skills/house-writing-style/SKILL.md` and
`scripts/style-lint.py`. Examples that contain prohibited forms live inside
fenced code blocks so the linter skips them.

## What this style is

STE-inspired plain technical English with project-specific spoken-style
constraints. It borrows controlled-English principles (direct sentences,
active constructions where clear, concrete verbs, controlled sentence
complexity, reduced noun stacking) and adds house rules. It is not formal
ASD-STE100 compliance; never claim certification.

## Hard rules (deterministic, ERROR)

| Rule | Detection | Fix |
|---|---|---|
| Em dash | the em dash character in prose | colon, semicolon, comma, or parentheses |
| Filler intensifiers | `genuinely`, `really`, `truly`, `actually` | delete the word |
| Slop words | `utilize`, `seamlessly`, `effortlessly`, `delve`, `game-changer`, `supercharge` | plain replacement or delete |
| Throat-clearing opener | "it is important to note", "it should be noted", "it's worth noting" | state the point directly |
| Artificial landing | "in conclusion", "to summarize", "all in all" | delete; end on the content |
| Decorative separator | six or more `= - _` characters as a line | blank line or heading |

## Soft rules (heuristic, WARN; model review decides)

- **Antithesis as rhetoric:** contrast used for style, not meaning. Technical
  contrast is exempt (see exceptions).
- **Corrective negation:** "not X, but Y" framing used as a rhetorical tic.
- **Negative parallelism / anaphora:** repeated "not only... but also" or a
  run of sentences opening with "not".
- **Formulaic rule-of-three:** three-part cadence used as decoration.
- **Setup and payoff beats:** "Little did X know" style narrative framing.
- **Repetitive parallel syntax:** consecutive sentences with identical
  grammatical shape.
- **Stacked noun phrases:** four or more nouns in a row; unpack or hyphenate.
- **Nominalization:** "perform validation of" for "validate".
- **Hedging:** stacked qualifiers where one decision word suffices.
- **Performed enthusiasm:** exclamation marks, "excited", emoji in prose.
- **Corporate-register verbs:** leverage, underscore in vague business use;
  technical use ("the API reflects the database state") is fine.
- **Long sentences:** over 45 words (reported).
- **Uniform cadence:** six or more sentences within a three-word length
  spread (reported as a review note, never a CI failure).

Regex cannot judge the semantic rules; the linter reports candidates and a
human or model review decides. Keep semantic rules as warnings.

## Protected spans (never linted, never rewritten)

Fenced code blocks, inline code, blockquotes (quotation fidelity), YAML
frontmatter, link URLs, raw HTML tags, logs, compiler output, JSON/YAML/XML,
hashes, paths, identifiers, citations, and copied upstream text. The linter
masks these before matching; the guard (if installed) refuses to rewrite
inside them.

## Sentence-length policy

"Vary sentence length unpredictably" is not mechanically checkable, so the
working rule is: avoid repetitive cadence; mix short and medium sentences when
the content supports it. The linter reports suspicious uniformity as a warning
and never fails CI on cadence.

## Precedence

1. User-requested style for a specific artifact wins where compatible with
   safety and task requirements.
2. Protected-content fidelity always wins over style.
3. House style applies to everything else the agent authors.
