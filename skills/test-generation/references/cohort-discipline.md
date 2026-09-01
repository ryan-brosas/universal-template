# File & Cohort Discipline

Source: Sewer56 and scarywood75, 2026-08-03; distilled from the original discussion transcript.

> Keep your files small. Group changes into cohorts — break a larger problem into smaller tasks, all coherently themed. Improves pass rate, and makes models have to think less.

## Rules

1. Small files: one clear responsibility; a file over ~300-500 lines is a red flag that the model will think *nexts* long.
2. Themed cohorts: a PR/change-set = one cohesive theme (e.g. "extract cache layer"), not soup of unrelated edits. This is what raises pass rate.
3. Turn things into code: e.g. "instead of asking the LLM 'order files in this way', make a CLI tool to verify it, and have the LLM call that" — the tool is deterministic; the LLM's free-form "ILooked" is not trustworthy.
4. Broad tests, narrow adoption: know what result you want; adopt only proven patterns; gates validate the copy/—don't a test suite to a repo because it has stars.
