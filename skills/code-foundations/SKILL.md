---
name: code-foundations
description: 'Use when a proven code pattern, primitive, or integration is worth reusing: encode it as a retrieval skill so future work reuses the shortcut instead of re-deriving it.'
disable-model-invocation: true
---
# Code Foundations

Code and tests are ground truth. A foundation is a compact retrieval map: it lets a constrained model find a proven primitive, understand the boundary it must preserve, and verify a safe port. It is not a re-description and never vendors modules.

## When to encode
A primitive is worth a foundation when it is recurring, proven (working + tested), and reusable beyond the feature that introduced it. Never encode a speculative or one-off implementation.

## The code-grounded loop
1. Prewalk - use Codebase Memory (or `codegraphcontext` when the repo is FalkorDB-indexed locally) to find the symbol, its callers, tests, and coverage.
2. Confirm - read exact source/excluded tests for each claim; pin commit+branch+license.
3. Encode - point to code first, then add code-shaped porting context that blocks wrong reuse.
4. Verify - keep a source test or direct probe; no behavior boundary, no foundation.
5. Route - add a leaf only for a new reusable trigger; never copy a whole repo into Markdown.

## Implementation capsules
A capsule contract answers one porting question with Path/Symbol, Signature, Data Shape, Flow, Invariant, Probe, Retrieve. Short interfaces/state/pseudocode belong only when the path+signature alone would let a small model port the wrong shape.
## Rules
- One active inspiration repo at a time; finish evidence + verification before the next project.
- Proven only; adopt/adapt/omit; pin provenance + coverage caveats.
- Constants/examples only when they change the decision.
- Prefer a short direct test probe over a long behavioural explanation.

## Verification
Every public line routes to a tested symbol + a named probe; capsule refs pass direct wiring and loader/map inspection; `git diff --check` is clean.
