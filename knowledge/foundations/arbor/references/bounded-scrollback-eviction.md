# Does bounded scrollback preserve a detached viewport's content?

Source: [penso/arbor](https://github.com/penso/arbor/tree/d8d82b7eec6cba3682374875d8f13407c7181ef0), revision `d8d82b7eec6cba3682374875d8f13407c7181ef0`, MIT (`LICENSE`). Local checkout: `<local-checkouts>/arbor`; origin and approved HEAD matched and the source tree was clean. Current project source, tests, requirements and runtime behavior outrank this historical evidence.

## Question and scope

When output evicts the oldest retained rows, can a detached viewport preserve rows that still exist? This is distinct from delayed-follow eligibility: not following the tail does not establish content anchoring. Trace below covers Arbor's default Alacritty-backed embedded path, not its daemon, SSH, Mosh or experimental Ghostty implementations.

## Retention to GUI flow

- `crates/arbor-terminal-emulator/src/lib.rs:22-26,154-168,221-256`: history defaults to 10,000 lines, with configuration bounded to 100–100,000. `TerminalEmulator::with_size` chooses the configured engine; `process` delegates. `alacritty_support.rs:51-66`, `new_state`, supplies `scrolling_history` to Alacritty's `Term::new`. Arbor delegates the retention algorithm to that dependency; the wrapper does not itself count dropped rows. Root `Cargo.toml:34` pins the Zed Alacritty fork at `9d9640d4`. Its internal eviction implementation was not read or executed in this pass.
- `crates/arbor-gui/src/terminal_backend.rs:340-368,428-457`: `spawn_reader_thread` parses PTY chunks under the emulator mutex, increments generation and notifies. EOF ends the loop; read errors append an error message, notify and break. Poisoned emulator/snapshot mutexes are recovered. Error output can itself consume history. `snapshot`/`shared_snapshot` (:191-229) refresh the cached `Arc<TerminalSnapshot>` when generation changes.
- `crates/arbor-terminal-emulator/src/alacritty_emulator.rs:47-69,96-117,133-146`: processing and resizing invalidate generation-keyed snapshots. `snapshot` packages output, styled rows, cursor and modes. `snapshot_tail` limits projection, not emulator retention. `alacritty_support.rs:104-124,126-143,180-214` projects the current topmost-to-bottommost grid range into zero-based vectors and maps the cursor relative to the current top. `lib.rs:42-54` exposes neither an absolute first-row identity nor an eviction/appended-row counter in the snapshot/process report.
- `crates/arbor-gui/src/types.rs:1051-1064,1241-1280`: the embedded runtime exposes shared snapshots, synchronizes by generation, and applies refreshed snapshots to sessions. `terminal_session.rs:359-407,459-491,558-598` derives follow eligibility and hashes the visible range; it does not translate a detached position using an eviction delta. `center_panel.rs:218-259` obtains the snapshot and renders the range selected by the scroll handle.
- `crates/arbor-gui/src/terminal_rendering.rs:214-300`: content extent derives from nonblank rows, cursor and selection; `terminal_visible_line_range` calculates row indices from negative pixel Y divided by line height. `terminal_render_slice_layout` uses that row index as a pixel offset. Thus the inspected GUI boundary anchors a retained-vector position, not an immutable logical line. If a prefix disappears while Y stays fixed, a different row occupies that position. The source does not establish a content-preserving compensation mechanism. This is a conditional source inference, not a reproduced Arbor native scroll defect; extent can also vary with cursor, blank tails and selection.

## Ownership and counterevidence

The emulator owns retention; the GUI owns pixel geometry. Changing a follow deadline cannot reconstruct row identity absent from the projection. Snapshot `Arc`s may keep an old projection alive but do not anchor the next projection. `terminal_backend.rs:303-328` makes close/last-owner drop attempt process termination; the reader loop exits on EOF/error. This study does not prove thread joining or prompt native cancellation.

Direct tests inspected, not run:

- `alacritty_emulator.rs:173-234`, `styled_lines_include_scrollback_content` and `plain_snapshot_output_includes_scrollback_content`: 120/220 lines establish history inclusion below the default cap, not eviction or detached anchoring.
- `lib.rs:385-400`, `sanitize_terminal_scrollback_lines_clamps_to_bounds`: configuration clamping only, not live retention.
- `terminal_rendering.rs:1962-2001`, `visible_render_signature_ignores_offscreen_scrollback_changes`: changes one offscreen header in an equal-length synthetic vector. It proves hashing excludes that content; it does not evict a prefix or drive a live emulator/scroll handle. No direct cap-plus-detached-viewport regression was located in the examined modules.

## Heddlework comparison and direct probe

`docs/terminal.md` promises detached anchoring. `src/ui/terminal-view.tsx:97-105` sets session-ID-addressed offsets. `src/terminal/service.ts:139-145,289-293` reads retained length before/after parsing and adds only positive length growth to a detached offset. `src/terminal/vt.ts:24,1376-1383,1405-1408` bounds history at 5,000 and removes its prefix on overflow. `snapshot` (:325-358) selects row `historyLength - offset + viewportRow`. At the cap, appended rows minus evicted rows is zero, so the service loses the movement signal even if the viewed rows survive.

A read-only `bun -e` probe used the production service with an injected push backend and no PTY. It spawned 16 columns × 3 rows, emitted `L0` through `L5002` joined by CRLF without a trailing newline, then detached at offset 10. After `\r\nL5003`, history stayed 5,000 and offset stayed 10, but visible rows changed from `L4990,L4991,L4992` to `L4991,L4992,L4993`. The original snapshot remained unchanged. This is avoidable drift: the old rows still exist. Detaching at offset 5,000 and appending `L5004` changed `L1,L2,L3` to `L2,L3,L4`; here the oldest anchor really expired, so preserving it is impossible and an explicit clamp policy is needed. Assertions characterized current behavior and exited 0; they do not certify correct anchoring.

`tests/terminal-service.test.ts:181-195` only covers growth below the cap. `tests/terminal-vt.test.ts:226-235` only asserts nonempty history/device response. Running both complete modules passed **24 tests / 95 assertions**. The injected probe disposed the service in `finally` and asserted listener removal and one process kill; production cleanup is at `service.ts:235-257`. No native window, upstream test, dependency setup or app modification was involved.

## Disposition

**ADAPT.** Preserve the retention/projection ownership split, but do not use Arbor's pixel position or Heddlework's net retained-length delta as proof of content anchoring. A local change should expose appended/dropped row progress or stable row identity, preserve surviving anchors, and define a clamp when an anchor is evicted. That is a recommendation, not an upstream algorithm copied or an implemented fix.

## Retrieval and next question

Use for cap saturation, prefix eviction and detached row identity, not delayed following. Direct source navigation only; existing graph `heddlework-inspo-arbor` was neither queried nor refreshed. Upstream freshness beyond the approved pin is unknown. The next bounded question is whether alternate-screen transitions preserve the distinction between active-screen mode, saved-buffer storage and primary-history ownership; see the separate alternate-screen capsule when available.
