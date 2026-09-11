# Why is appearance delivery deferred beyond the current app update?

Source: `remorses/zed` at `8b94defe56992b3ca4ffd4853ace741d8168111a`; repository license files LICENSE-APACHE and LICENSE-GPL. This capsule covers GPUI, not the whole editor. Inspect file-level licensing before copying.

## Flow and ownership

`crates/gpui_linux/src/linux/xdg_desktop_portal.rs:26-131`, `XDPEventSource::new`, spawns a background settings reader. It sends initial color scheme if available, then receives a change stream through calloop's channel. The mapping at :185-191 makes NoPreference Light. Initial read failure does not itself prevent attempting subscription; subscription/stream errors terminate the async path. The spawned work is detached: this is not evidence of a per-window cancellation API.

`crates/gpui/src/window.rs:1695-1710` installs `platform_window.on_appearance_changed`. It clones the async app context and foreground executor, then queues the window update. The source comment explains the reentrancy hazard: AppKit can synchronously call back while App is borrowed. Deferral releases that borrow before `Window::appearance_changed` (:2506-2512) reads platform appearance and invokes retained observers.

## Invariants and failure boundaries

Appearance observers see refreshed window state, not just a raw portal value. A synchronous platform event does not immediately run observers inside the currently borrowed app update. A failed window-handle update is logged; the callback does not reconstruct a dead window. Foreground deferral is a borrow/lifecycle seam, not an exactly-once queue or cancellation guarantee. Portal mapping and native window propagation are different layers.

## Direct test

`window.rs:7163-7185`, `test_appearance_change_runs_after_app_update`, retains the observer subscription, simulates Dark inside `cx.update`, asserts the observed value is still None, runs until parked, then asserts Dark. It proves deferred delivery in TestAppContext. It does not prove real Linux portal delivery, subscriber disposal, coalescing, or shutdown behavior. Test source read directly; upstream tests not executed and no setup performed.

## Heddlework boundary

`src/ui/theme-manager.ts` currently owns monitor processes, polling and watcher disposal rather than a GPUI observer. Its platform detector uses gsettings on Linux. Replacing those with bridge events would need a TypeScript subscription and inverse cleanup; the GPUI test alone does not prove that bridge. Current project source, tests, requirements, and runtime behavior outrank this historical evidence.

**Disposition: ADAPT.** Preserve deferred delivery and retained subscription ownership if exposing native appearance through the downstream bridge. Add a bridge-specific teardown test rather than assuming a portal listener is a disposable window subscription.

## Retrieval and scope

Read the exact ranges and named test above. Existing full index: `heddlework-inspo-zed-gpui-pin`; this bounded pass used direct source, not graph completeness claims. Excludes editor themes, unrelated Zed subsystems, and all live-native guarantees.

## Deepening pass 1: what does dropping the subscription cancel?

Question: What exactly is removed on drop, and what happens to queued appearance work or window destruction?

### Registration, cancellation and queued work

- `crates/gpui/src/window.rs:1964-1978`, `Window::observe_window_appearance`, inserts under emitter key `()`, immediately activates, and returns the RAII handle. Its callback always returns true; ordinary withdrawal is subscription drop.
- `crates/gpui/src/subscription.rs:46-87,188-194`, `SubscriberSet::insert` and `Subscription::drop`, connect the handle to one subscriber ID. Drop sets the shared `dropped` flag, removes that ID when the map is available, and removes the emitter entry if empty. It does not unregister `platform_window.on_appearance_changed`, cancel the portal reader, or cancel foreground tasks. `Subscription::detach` (:162-168) discards the unsubscribe closure instead: dropping the detached handle is not cancellation.
- `window.rs:1695-1714,2506-2512` queues a detached task containing a window handle, not a snapshot of observer callbacks or an appearance value. At execution, `appearance_changed` reads the then-current platform appearance and walks the then-current subscriber set. Therefore dropping before delivery prevents that observer call but does not cancel the queued window update. Multiple queued tasks need not preserve intermediate appearance values; this is source inference, not a tested coalescing guarantee.
- `subscription.rs:110-144` checks the dropped flag around invocation. Drop cannot undo an observer already executing. If delivery has temporarily taken the map, logical withdrawal uses the flag and physical callback removal follows during retention. See the [mutation capsule](observer-mutation-during-delivery.md) for same-turn effects.

### Window and entity lifetime are separate

`window.rs:6631-6637,6663-6675`, `AnyWindowHandle`, is a Copy identifier, not an owning window reference. `app/async_context.rs:85-96`, `AsyncApp::update_window`, rejects a released app, borrow failure, or quitting app. `app.rs:1875-1930`, `App::update_window_id`, rejects an absent window with `window not found`. The queued task logs an update error and does not recreate the window.

`window.rs:2034-2037`, `remove_window`, only marks `removed`. Actual removal happens in the update's trailing cleanup (`app.rs:1886-1925`), including handle/window registries, entity tracking and close observers. Marking removal from an appearance observer does not itself stop the remaining appearance observers in that delivery: `appearance_changed` does not check `removed` between callbacks.

A surviving Subscription owns an Rc to subscriber state (`subscription.rs:9-11,67-85`). Destroying the window removes its delivery owner but does not necessarily release callback captures immediately: an externally retained handle can keep that state alive until unsubscribe. Conversely `Context<T>::observe_window_appearance` (`app/context.rs:461-477`) captures a weak entity and returns `view.update(...).is_ok()`; failed entity update removes this observer on delivery. Neither wrapper is proof of synchronous per-entity cleanup at entity destruction.

### Direct tests and limits

`subscription.rs:327-350`, `test_subscription_drop`, exercises production global registration and notification: drop before notification produces zero calls. Global delivery really uses `SubscriberSet::retain` (`app.rs:1816-1821`), but this is not an appearance queue/window-destruction test. The appearance regression at `window.rs:7162-7185` retains its handle throughout. Its test platform helper (`platform/test/window.rs:158-167`) changes appearance and invokes the installed platform callback; it does not model native destruction. No direct dropped-appearance-before-drain or destroy-window-before-drain test was located in the inspected seam. Upstream tests were read, not run.

### Heddlework comparison and direct probe

`src/ui/app.tsx:61-63` subscribes via `useSyncExternalStore`; `src/main.tsx:89-99` disposes the theme manager before kernel disposal. `src/ui/theme-manager.ts:75-78,114-123` removes individual JS listeners and clears all listeners during LIFO source cleanup. This is not GPUI RAII nor cancellation of already retained callbacks. The gsettings stdout handler (:150-158) calls `refreshSystemTheme` without a started guard and is not detached by cleanup; error/exit fallback does have a guard. Refresh (:103-112) can still change the snapshot and global palette after disposal.

A read-only `bun -e` probe imported the real ThemeManager with an injected EventEmitter stdout and fake kill (no process spawn, filesystem write or native app). It started/disposed the manager, changed an injected resolver to light, then emitted stdout data. Assertions passed: one SIGTERM request, zero listener notifications, one retained stdout listener, snapshot and nativeTheme changed to light. This demonstrates the callback boundary, not that a real child necessarily emits after SIGTERM. It distinguishes withdrawing listeners from making queued producer callbacks inert.

`bun test ./tests/theme-manager.test.ts ./tests/theme-omarchy.test.ts` passed: 15 tests, 43 assertions, exit 0. The tests cover system mode, fallback and cleanup requests; the watcher-disposal test (:219-235) checks its fake dispose flag, not queued callback suppression. No application code changed.

Disposition remains **ADAPT**: preserve separate subscription withdrawal and delivery-owner lifetime checks for any native bridge; pair cleanup with a late-delivery guard where the bridge promises inert teardown. Do not equate unsubscribe with canceling the platform producer or queued task. This pass refines the existing seam rather than creating a duplicate capsule.

Next question: how do insertions, self-drop and dropping another observer interact within one delivery? Answered by the linked second-pass capsule. Live native close/queued-event behavior remains unverified.
