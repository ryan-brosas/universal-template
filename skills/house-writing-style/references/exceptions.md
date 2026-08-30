# House style exceptions

## Technical contrast

Anti-rhetoric rules target contrast used for style. Contrast that carries
technical meaning stays:

- "Use the thread ID, not the comment ID."
- Input/Output, Allowed/Rejected pairs in tables and docs.
- Diff-style before/after blocks.

The linter's `negative-parallelism` warning is a review note. When the
contrast carries meaning, keep it and ignore the warning.

## Parallel structure

Technical lists, schemas, and step sequences stay grammatically consistent.
The undesirable behavior is formulaic prose: consecutive rhetorical sentences
with identical shape. Lists are exempt by design.

## Quotation fidelity

Quotations, citations, copied upstream text, and user-provided source stay
exact even when they violate every rule. The linter skips blockquotes; the
output guard refuses to rewrite them.

## User-requested style

When a user explicitly requests another style for a specific artifact
(literary tone, API format, legal template, copied source format), follow the
user's choice where compatible with safety and task requirements. The house
style is the default, not an override.

## Domain terminology

Plain English applies to the explanation. Technical terms stay when precision
requires them: keep `idempotent`, `backpressure`, `CRDT`, `HNSW`. Do not
simplify a term into inaccuracy.

## Non-prose surfaces

Commit subjects follow the repository's commit convention (conventional
commits here); style-lint does not run on commit messages. Code comments get
only the high-confidence lexical rules when a project opts in. Generated
files, vendored code, lockfiles, fixtures, and reference corpora stay out of
scope.

## STE boundary

This house style is STE-inspired. It is not certified ASD-STE100 prose and no
output may be described as ASD-STE100 compliant unless a current, formal
compliance process says so.
