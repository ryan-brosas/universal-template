# Can subscription changes affect the current appearance delivery?

Source: [remorses/zed](https://github.com/remorses/zed) at `8b94defe56992b3ca4ffd4853ace741d8168111a`. Repository licenses: LICENSE-APACHE and LICENSE-GPL; inspect file-level obligations before copying. Paths below are relative to that checkout unless marked Heddlework. This is the second bounded question of this round, following [cancellation and window lifetime](deferred-appearance-delivery.md).

## Uncertainty and production flow

Does delivery iterate a fixed collection, and can an earlier observer cancel a later one, remove itself, or add a listener that runs immediately?

`crates/gpui/src/window.rs:1964-1978,2506-2512`, `Window::observe_window_appearance` and `Window::appearance_changed`, register immediately active callbacks and deliver through a cloned `SubscriberSet` sharing the same state. The clone is not a callback snapshot.

`crates/gpui/src/subscription.rs:46-87`, `SubscriberSet::insert`, allocates monotonically increasing subscriber IDs in a BTreeMap. Its unsubscribe closure holds both a shared dropped flag and the set state. `SubscriberSet::retain` (:110-144) takes the emitter's current map out of shared state, leaving an Option slot. It releases the RefCell borrow before calling observers. Delivery walks the taken map in ID order, skips inactive subscribers, removes active dropped subscribers before invocation, and tests the dropped flag again after invocation. The final step merges registrations made while callbacks ran and puts surviving subscribers back.

## Invariants, ownership and counterevidence

- A can drop later B before B is visited: B's flag changes even while its entry is outside the shared map; B is skipped in this delivery. Removal is not merely a future-event promise.
- Self-drop cannot cancel the invocation in progress, but the post-call flag check prevents reinsertion. If A also inserts C, the new shared map does not hide A's dropped state in the temporarily taken map.
- C is not visited by this outer retain traversal: it is merged after traversal, even though window appearance registration activates immediately. This is source-derived for appearance delivery, not directly asserted by the tests below.
- This is not a universal ban on reentrancy. A nested retain on the same emitter sees no map unless an insertion has populated the shared slot; in that case it can see those new subscribers. Do not translate outer-traversal isolation into a guarantee covering arbitrary recursive delivery. Ordinary native appearance entry queues work rather than directly recursing (`window.rs:1695-1714`). No nested-appearance test was located in the inspected seam.
- These guarantees belong to `retain`, not every SubscriberSet API. `remove` (`subscription.rs:89-106`) extracts callbacks and filters activation; it does not provide the same around-invocation dropped checks.
- Callback return false removes an observer. The window wrapper returns true, while the entity-context wrapper returns whether weak-entity update succeeded (`app/context.rs:461-477`). Neither retention nor its wrapper catches callback panics; normal-return cleanup should not be advertised as panic recovery.

## Direct tests: what they actually prove

The tests in `crates/gpui/src/subscription.rs` use TestApp and production global observers, not a separate subscriber imitation:

- :207-256, `test_unsubscribe_during_callback_with_insert`: A self-drops and inserts a detached no-op observer; B self-drops. Both counters stay at one after a second update. This catches orphaned old subscribers, but does not count the new observer or assert its first delivery time.
- :258-296, `test_callback_dropped_by_earlier_callback_does_not_fire`: A drops B, whose counter remains zero in the same update.
- :298-325, `test_self_drop_during_callback`: one call, then none on the next update.
- :327-350, `test_subscription_drop`: dropped before notification yields zero calls.

`crates/gpui/src/app.rs:2085-2100`, `App::observe_global`, defers activation, unlike immediate appearance activation. Global notification processing invokes the same production `retain` (`app.rs:1816-1821`). Thus the tests support shared withdrawal mechanics but do not prove appearance activation timing, native callback ordering, window destruction or recursive delivery. All upstream tests were inspected, not executed; no dependencies/setup were run. The existing appearance test (`window.rs:7162-7185`) proves deferral only, not mutation during a delivery.

## Heddlework comparison and probe

Heddlework `src/ui/theme-manager.ts:75-78,227-229` uses a live JavaScript Set: unsubscribe deletes a listener; `#emit` iterates that Set directly. React obtains its cleanup through `useSyncExternalStore` (`src/ui/app.tsx:61-63`), and runtime disposal clears the listeners (`src/ui/theme-manager.ts:114-123`; `src/main.tsx:89-99`). The inverse lifecycle is explicit, but current-turn insertion semantics differ from GPUI's taken map.

A read-only `bun -e` probe imported the real ThemeManager, disabled preference writes, and injected a constant resolver. It registered A then B; A removed B and registered C during a single `setMode('light')`. The direct assertion passed with order `["A", "C"]`: removal suppresses B, but insertion runs C in the same emit. It then disposed the manager and restored the in-process theme. No application/test file was changed. This proves this synchronous ThemeManager path, not React commit timing or native delivery.

The full relevant local modules passed with exit 0: `bun test ./tests/theme-manager.test.ts ./tests/theme-omarchy.test.ts` — 15 tests, 43 assertions. Existing tests exercise theme modes, event-source fallback and disposal requests; they do not lock mutation-during-notification behavior. The probe is additional evidence, not a newly committed regression test.

## Disposition and next question

**ADAPT.** If a native appearance bridge needs stable per-turn observer membership, preserve GPUI's distinction between the delivery set and newly registered listeners while retaining same-turn cancellation. Do not substitute a raw JS Set and assume equivalent insertion behavior; do not change Heddlework's current semantics without an explicit contract and bridge-specific tests. Source mechanism and lifecycle differ enough to reject blind transfer.

NEXT: when several platform appearance events arrive before the foreground queue drains, which values and how many notifications are delivered? The queued task reads current state rather than carrying an event value, but intermediate-value loss and duplicate delivery lack direct tests in this inspected seam. Stop this round after two questions; no live-native or exhaustive repository claim.
