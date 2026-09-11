# Zed GPUI evidence index

## Provenance

- Upstream: https://github.com/remorses/zed
- Revision: `8b94defe56992b3ca4ffd4853ace741d8168111a`
- License: repository LICENSE-APACHE and LICENSE-GPL; inspect file-level obligations before copying
- Checkout: `<local-checkouts>/gpuix-heddlework-pin/zed`
- Existing full-mode index: `heddlework-inspo-zed-gpui-pin`

Origin and HEAD matched the approved pin; the checkout was clean. This round used direct source and test reads, not graph queries: graph coverage validation was not applicable. No reindexing, remote updates, checkout changes, upstream dependency installation or setup occurred. Current project source, tests, requirements and runtime behavior outrank this historical evidence.

## Complete capsule inventory

1. [Deferred appearance delivery, subscription cancellation and window lifetime](deferred-appearance-delivery.md) — Original deferred-delivery study preserved and refined in round pass 1: what dropping an observer removes; why queued window updates survive unsubscribe; dead-window lookup; retained subscriber state. Disposition: ADAPT.
2. [Observer mutation during delivery](observer-mutation-during-delivery.md) — Round pass 2: self-drop, dropping a later callback, newly inserted callbacks, production retain mechanics versus global test activation and JS Set behavior. Disposition: ADAPT.

Inventory: two capsules total; this round refined one existing capsule and added one. Each has exact source/test anchors, lifecycle and failure boundaries, counterevidence, Heddlework comparison and a next question. This is not exhaustive GPUI learning.

## Results and limits

The earlier deferred-delivery study inspected `test_appearance_change_runs_after_app_update`; its historical local comparison ran window, theme, terminal-key and terminal-service modules together (27 tests, 88 assertions). Those historical results are not a new run this round.

This round inspected four SubscriberSet regression tests using production global notification, plus the appearance test and its test-platform helper. Global activation is deferred whereas appearance activation is immediate. These tests do not establish appearance unsubscribe-before-drain, destroy-before-drain, insertion timing or live Linux delivery. Upstream tests were not executed.

Current local verification: `bun test ./tests/theme-manager.test.ts ./tests/theme-omarchy.test.ts` passed, 15 tests and 43 assertions, exit 0. Two direct injected `bun -e` probes passed:

- After disposal, a retained fake stdout callback still changed the real manager snapshot/global theme, while subscriber notifications stayed zero and SIGTERM was requested once. This is a late-callback boundary, not proof of actual process behavior after kill.
- During one real ThemeManager notification, A removed B and inserted C: observed order was A,C. This differs from GPUI's outer taken-map traversal.

No app/test code changed. No live native runtime, portal delivery, panic recovery or exhaustive close-race coverage is claimed. Local Markdown links, cited source ranges/symbols and cold foundation metadata are verification targets; their validity alone does not prove runtime behavior.

## Retrieval and next bounded question

For cancellation or queued callbacks, load capsule 1. For callback mutation or ordering, load capsule 2. Source-relative paths reconnect to the checkout and portable revision above; Heddlework paths are explicitly identified. Local link and capsule inventory completeness concern this foundation only.

NEXT: burst appearance events before foreground drain — current-state sampling, intermediate-value loss and duplicate notifications. Two questions are complete for this round; main reviews before further study.
