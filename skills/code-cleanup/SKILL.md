---
name: code-cleanup
description: "Use when behavior works but the diff is noisy, repetitive, over-complicated, or AI-shaped - lock behavior first, simplify the changed code, and re-verify without expanding scope."
invocation: entry
---


# Code Cleanup

## When to Use

Tests/build/typecheck pass but the diff is clumsy; feature works but has duplication, over-nesting, dead code, awkward naming; final simplification before review/merge; "broken window" needs boarding up.

## When NOT to Use

Behavior is broken or unverified; "cleanup" is cover for redesign; cleanup spreads to unrelated files; can't prove nothing broke.

## Core Principle

**Lock behavior first. Then simplify. Then re-verify.** Sequence: behavior locked → simplify → re-verify nothing changed. If any step fails, stop.

## Workflow

1. **Lock behavior.** Run the relevant tests + typecheck + lint. Save the output. This is your "before" baseline.
2. **Identify smell.** Use `fallow` (if available) for dead code, dupes, complexity. Otherwise: read the diff, mark spots that feel off.
3. **Simplify, in order:**
 - **Delete** (dead code, comments that restate, unused exports), easiest, highest impact
 - **Rename** (clearer names, remove prefixes/suffixes), cheap, high signal
 - **Extract** (a variable, a helper), only if nameable and reused
 - **Inline** (a one-use wrapper), only if the wrapper adds no clarity
 - **Restructure** (split a function, lift a conditional), last resort, highest risk
4. **Re-verify.** Same tests, same typecheck, same lint. Outputs match "before" baseline.
5. **Diff review.** Anything outside the cleanup scope? Split it out.

## Anti-Simplification Patterns

- Adding an abstraction for "future use", speculative, not cleanup
- "Improving" the architecture under cover of "cleanup", separate change
- Renaming things the user named (breaks their mental model)
- "Fixing" unrelated lint warnings in the same diff
- Reformatting the whole file (no behavior change, but noise in diff)

## Common Mistakes

Cleanup before behavior is locked (you can't prove nothing broke). Expanding scope (renaming across the codebase). Adding abstractions for "future reuse". Deleting without checking consumers. Reformatting the whole file. "Improving" code style in unrelated parts. "We'll add tests after" (the tests are how you prove nothing broke).

## Red Flags

Cleanup before tests pass; "I just want to refactor this"; expanding into unrelated files; "while I'm here" fixes; tests deleted (not the cleanup target); reformatting the whole file; rename of public API; no baseline saved; re-verify skipped; "I'll write tests for the new structure later".


## Verification

Same tests, typecheck, and lint re-run after cleanup; outputs match the saved "before" baseline; every change is a deletion or simplification scoped to what was noisy.


## References

N/A, no reference files; this skill is self-contained.
