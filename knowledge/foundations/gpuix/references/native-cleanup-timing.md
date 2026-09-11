# When does native resource cleanup follow retained-tree deletion?

Source: [remorses/gpuix](https://github.com/remorses/gpuix) at `a24b4a42eb516c7b940eb8d34ecebb077df623bd`, Apache-2.0. Upstream paths below are source-relative. Historical evidence; current project source and runtime behavior outrank it.

## Question and execution path

Does deleting a retained node synchronously destroy its custom adapter and native event subscriptions? Does the test teardown establish production shutdown behavior?

`packages/native/src/retained_tree.rs:242-273`, `destroy_element`, only removes retained nodes and returns IDs. `packages/native/src/renderer.rs:1193-1200`, `apply_batch`, applies the tree mutation and requests invalidation. Neither calls a custom adapter's destroy method.

The next `GpuixView::render`, `renderer.rs:3809-3844`, locks the tree, syncs focus handles, calls `custom_registry.prune_missing`, and retains only live scroll handles, virtual lists and motion states. Cleanup of these view-owned resources is render-driven, not part of the deletion receipt returned to JS.

`renderer.rs:3725-3806`, `sync_focus_handles`, removes subscriptions whose element/event no longer exists and removes focus handles no longer needed. Focus/blur subscriptions capture clones of the event emitter. The GPUIX evidence shows those owning map entries being dropped; exact GPUI dispatch/frame closure release semantics are outside this source lane.

`packages/native/src/custom_elements/mod.rs:296-318,351-385`: `get_or_create` destroys an old adapter before reusing an ID for a different type. `prune_missing` collects absent IDs before calling `destroy`, which removes each registry entry and calls its adapter's `destroy`. `destroy_all` explicitly empties the registry while an App is alive. `packages/native/src/custom_elements/input.rs:474-476` clears the input's Entity state in `destroy`.

## Invariants and counterevidence

Retained-node lifetime, JS-handler lifetime and rendered-resource lifetime are distinct. A successful deletion batch does not certify that a subsequent frame has run. Failure to invalidate after mutation can both delay render-driven pruning and lose the JS destruction receipt; see [event destruction](event-destruction.md).

The existence of `destroy_all` does not prove production calls it. `packages/native/src/test_renderer.rs:45-80`, `VisualTestState::drop`, explicitly clears the root, destroys all adapters, clears focus subscriptions/handles, requests an empty frame and runs until parked. Its comment identifies extra input-handler Entity clones held in the rendered frame and platform window. This is a test-only teardown implementation, not a production shutdown guarantee.

By contrast, the inspected Linux/Windows/FreeBSD `GpuixRenderer::drop`, `renderer.rs:2796-2801`, takes the UI command sender. It does not itself call `destroy_all` or force an empty frame. No `GpuixView`/registry Drop hook invoking `destroy_all` was located in the inspected GPUIX files. Ordinary Rust field drops may release resources, but equivalence to the explicit test teardown is not established. Do not infer a leak or a safe production shutdown solely from that difference.

## Direct test evidence and gaps

`custom_elements/mod.rs:487-503`, `reusing_an_id_for_another_type_destroys_the_previous_adapter`, checks one destroy call using a RecordingElement. It does not render or exercise missing-node pruning, platform handles, or production shutdown. The adjacent prop-sync test checks changed/removed properties, not disposal.

`packages/react/src/__tests__/mutation-lifecycle.test.tsx:123-151` checks retained-node counts after removed text/subtrees. That measures tree storage, not native adapter, subscription, TSFN or input-handler release. `test_renderer.rs:174-179` stores events in a synchronous Vec rather than the production ThreadsafeFunction queue. No direct production teardown or post-delete-before-next-frame resource test was located in this bounded search. Upstream tests were inspected, not executed; no setup or dependencies installed.

## Heddlework comparison and disposition

Heddlework's downstream `patches/gpuix-0.7.0-heddlework.patch:3187-3246,3253-3263` implements `BrowserRuntime::retire_active_browser`, `destroy`, and `Drop`. Retirement disables emissions, cancels pending commands, hides/closes native views and releases runtime references. `:3650-3666`, `browser_client`, wraps the emitter in an `events_enabled` check. These are downstream safeguards, not features of the pinned upstream. Disabling emissions cannot retract payloads already queued before retirement.

`src/browser/service.ts:178-229,337-343` therefore remains the authority for rejecting obsolete generations and disposed owners; `src/ui/browser-host.tsx:39-73` supplies generation-keyed instances. `src/ui/terminal-view.tsx:187-215` separately guards missing native IDs, clears the ID through its ref callback, and returns the frame-subscription inverse from `useLayoutEffect`. Component/service cleanup is not delegated to eventual native repaint.

`tests/browser-service.test.ts:97-134` checks stale generations and service recreation/disposal. The complete module passed in this round: 12 tests, 73 assertions, exit 0. `tests/browser-ui.test.tsx:30-54` uses unmount in a finally block, but that cleanup call is not an assertion about native browser resource release; these native-gated UI tests were inspected, not run. The injected event-routing probe from pass 1 does not prove native pruning timing.

**Disposition: ADAPT.** Treat render-driven pruning as one cleanup layer, not an owner-lifetime acknowledgement. Preserve Heddlework's explicit component/service inverses and downstream native retirement guards; require independent production teardown evidence before relying on test-only empty-frame cleanup. No app or test code changed.

## Scope and next question

This second pass stops at GPUIX-owned cleanup scheduling and the test/production boundary. Direct source navigation only; no graph claims. NEXT: can the public applyBatch bridge preserve destruction receipts when post-mutation invalidation fails, and what deterministic native test can distinguish that failure from validation rejection? This is a future bounded study, not an implemented fix or a third pass.
