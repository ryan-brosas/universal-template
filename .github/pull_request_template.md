## Summary

<!-- what changed, stated as the user-visible result -->

## Why

<!-- the problem this solves; reference an issue when one exists -->

## Verification

<!-- only checks actually run, with results -->

- Review changed instructions, metadata, references, and callers; report focused tests when executable helpers change.
- Local review: source/dependency impact and diff quality; Sourcebot baseline when applicable; IDE checks only when opted in.
- Sourcebot bot review: PENDING / PASSED / BLOCKED, with PR/base/head, completion evidence and finding dispositions. Local readiness or no comments is not a passed bot review.
- `git diff --check`

## Risks

<!-- regression / compatibility / migration / performance / security — or None identified -->

## Reference / Prior Art

<!-- when external code materially influenced this change: repo, path, revision, ADOPT/ADAPT/INSPIRATION. Else: N/A -->

## Visual Evidence

<!-- for visual changes: rendered/runtime proof. Model review is not rendered proof. Else: N/A -->

## Breaking Changes / Migration

<!-- if applicable: what breaks and how to migrate. Else: N/A -->
