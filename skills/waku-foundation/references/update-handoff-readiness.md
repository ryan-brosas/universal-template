# When does a Linux update handoff become safe to discard rollback state?

Source: [egoist/waku](https://github.com/egoist/waku/tree/1114d4c5bdd3baf1454667bd7dd73ddd767a4767), `1114d4c5bdd3baf1454667bd7dd73ddd767a4767`, GPL-3.0-only. Architecture-only evidence; no implementation copying. Checkout `<local-checkouts>/waku`; origin and HEAD reverified, working tree clean. Current project source, tests, requirements and runtime behavior outrank this historical evidence.

## Question and ownership transfer

Is the helper's READY acknowledgement equivalent to successful installation? No: helper acceptance and replacement startup are separate milestones.

`src/updater/linux.rs:105-137` gives `StagedUpdate` cleanup ownership until `disarm`. `install_available_update` (:259-341) takes staging out of the mutex, starts a worker and helper, and reads one stdout line. READY disarms staging cleanup, attempts to send `QuitAndInstall`, and waits for the helper. Invalid acknowledgement kills/waits the helper, returns status to Idle and attempts a Failed event; the still-armed update is dropped. Helper-spawn and channel-send errors preserve the same staging cleanup ownership.

The read has no deadline in this path. Both event sends ignore failure. A helper that never replies can leave the worker waiting; READY is not proof the UI consumed its quit request. These are source-level failure boundaries, not reproduced hangs.

`src/bin/waku-updater.rs:55-75` validates before printing/flushing READY, waits for its parent, then calls `apply_update`. Thus READY precedes directory replacement.

## Activation, rollback and startup policy

`src/bin/waku-updater.rs:206-291` moves the old install to a unique backup, then moves staging into the install path. A failed second rename attempts restoration. Startup-path reservation or launch failure invokes rollback. Rollback moves the failed install aside, restores backup, removes the failed tree best-effort, records the error and relaunches the old build. Restoration itself can fail; this is not unconditional recovery.

`wait_for_relaunch` (:312-331) checks readiness-file existence before child status. Ready removes the backup; early exit rolls back. Timeout, or inability to observe child status, retains the new install and backup rather than replacing a possibly running executable. The timeout is therefore not an automatic rollback trigger. The READY stdout line is distinct from this later readiness file.

Individual renames do not make the two-rename sequence a crash transaction. There is an interval with no install directory. `sync_directory` (:381-383) ignores sync errors. This pass establishes handled-error policy, not power-loss durability, automatic crash recovery or a transaction journal.

## Direct test limits

Tests were inspected, not executed:

- `directory_swap_can_be_rolled_back_without_merging` (:445-463) performs rename operations directly; it does not call production rollback or inject rename failure.
- `full_handoff_waits_for_startup_and_removes_the_rollback_copy` (:465-504) calls production `apply_update` with a shell fixture that writes the readiness file. It verifies replacement contents and backup removal. Despite its name, it bypasses helper main, stdout acceptance and parent waiting. The fixture does not open a real application window.
- `src/updater/linux.rs:790-850` tests key/version/extraction/preferences, not the worker's acknowledgement timeout, ignored event send or crash interruption.

No updater, helper, upstream tests or fixtures were executed. No live startup or crash probe is claimed.

## Heddlework comparison and disposition

`scripts/build.ts:27-65` removes the development dist directory and produces a compiled artifact; its finally block cleans temporary CEF staging. That is build-output ownership, not a running-install replacement protocol. This study does not turn successful compilation or temporary cleanup into evidence of update safety.

**ADAPT** the distinction between helper acceptance, installation activation and replacement readiness if Heddlework later adds a managed updater. Preserve explicit ownership transfer and a non-destructive policy for a still-running unacknowledged replacement. Do not transfer GPL implementation or call the inspected sequence crash-proof.

Next: whether helper validation and any subsequent recovery path can safely identify abandoned backup/staging directories after interruption. Validation internals and automatic recovery remain outside this pass. Direct navigation only; no indexing, installation or application edits.
