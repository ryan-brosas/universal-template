---
name: gpuix
description: "Use when consulting pinned GPUIX evidence for window-option normalization, queued-event destruction, or render-driven native cleanup."
kind: foundation
---
# GPUIX foundation

Historical evidence from [remorses/gpuix](https://github.com/remorses/gpuix) at
`a24b4a42eb516c7b940eb8d34ecebb077df623bd`. License: Apache-2.0.
Local convenience checkout: `<local-checkouts>/gpuix-heddlework-pin`.

Current project source, tests, requirements, and runtime behavior outrank this
projection. This is cold source evidence, not a procedure or exhaustive study.

Open [the index](references/index.md), then load only the matching capsule:

- [Window-option normalization](references/window-option-normalization.md): omitted values versus explicit false.
- [Event destruction](references/event-destruction.md): queued delivery, handler removal and the post-mutation invalidation failure boundary.
- [Native cleanup timing](references/native-cleanup-timing.md): render-driven pruning versus test-only shutdown cleanup.

Revalidate the pinned implementation and direct tests before reuse.
