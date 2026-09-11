---
name: zed-gpui
description: "Use when consulting pinned Zed GPUI evidence for deferred appearance observer delivery and subscription ownership."
kind: foundation
---
# Zed GPUI foundation

Historical evidence from [remorses/zed](https://github.com/remorses/zed) at
`8b94defe56992b3ca4ffd4853ace741d8168111a`. License: repository LICENSE-APACHE and LICENSE-GPL; inspect file-level obligations before copying.
Local convenience checkout: `<local-checkouts>/gpuix-heddlework-pin/zed`.

Current project source, tests, requirements, and runtime behavior outrank this
projection. This is source evidence, not a procedure or an exhaustive repository study.

Open [the index](references/index.md), then load only the matching capsule:

- [Deferred delivery, cancellation and window lifetime](references/deferred-appearance-delivery.md): unsubscribe versus queued work and delivery-owner destruction.
- [Observer mutation during delivery](references/observer-mutation-during-delivery.md): self-drop, later-observer cancellation and insertion timing.

Two bounded questions deepened this evidence; native queue/close behavior remains unexecuted. Revalidate the pinned implementation and direct tests before reuse.
