# GPUIX evidence index

## Provenance

- Upstream: https://github.com/remorses/gpuix
- Revision: `a24b4a42eb516c7b940eb8d34ecebb077df623bd`
- License: Apache-2.0
- Checkout: `<local-checkouts>/gpuix-heddlework-pin`
- Existing full-mode index: `heddlework-inspo-gpuix-0.7.0`

Origin and HEAD were reverified against the approved pin; the checkout was clean.
These passes used direct source/test reads, not graph navigation. No reindex,
remote update, checkout change, dependencies or setup scripts were run.
Current project source, tests, requirements and runtime behavior outrank this evidence.

## Complete capsule inventory

- [Window-option normalization](window-option-normalization.md) — How do omitted fields differ from explicit false, and where do native defaults apply? Prior capsule preserved; ADAPT.
- [Event destruction](event-destruction.md) — Can queued native payloads invoke removed handlers? Successful-batch lookup suppression, persistent IDs, and the lost destruction-receipt failure boundary; pass 1, ADAPT.
- [Native cleanup timing](native-cleanup-timing.md) — When do custom adapters and focus subscriptions release, and does test teardown prove production shutdown? Render-driven pruning and explicit test-only empty-frame teardown; pass 2, ADAPT.

## Scope, evidence and limits

Three focused capsules, not repository-wide coverage. The latest round studied two successive questions and added two capsules. Each records exact source/test spans, ownership, counterevidence, Heddlework comparisons and one disposition.

Prior normalization evidence: mapper tests distinguish defaults, omission and independent focus/show flags. The earlier local window/theme/terminal-key/terminal-service run passed 27 tests, 88 assertions; that result was not rerun or promoted to native verification in this round.

Latest round: `bun test ./tests/browser-service.test.ts` passed 12 tests, 73 assertions (exit 0). A setup-free Bun probe imported upstream's actual event-registry and batch-renderer with an injected renderer: pre-flush handlers remain; successful returned IDs clear handlers; late delivery is suppressed; a thrown batch leaves mappings; owner detachment suppresses dispatch. The injected failure is not a live Rust/TSFN race.

Upstream direct tests were inspected, not executed. No live-native behavior was verified. In particular, malformed-batch tree-helper atomicity does not prove the N-API call is atomic after repaint notification fails; retained-node counts do not establish native-resource release; test-only teardown is not production teardown evidence. No application code changed.

## Retrieval and next question

For stale delivery select event destruction; for native release timing select native cleanup timing; for optional window fields select normalization. Local Markdown links and cited source ranges are mechanically checked; semantic usefulness comes from the traced boundaries and explicit test limits, not metadata alone. Inventory completeness concerns this foundation only.

NEXT: preserving destruction receipts across a post-mutation invalidation failure, with a deterministic native boundary test. Stop this round after two questions for main review; no broad completion claim.
