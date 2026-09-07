# Is saved alternate-buffer storage the same as active alternate-screen mode?

Source: [penso/arbor](https://github.com/penso/arbor/tree/d8d82b7eec6cba3682374875d8f13407c7181ef0), revision `d8d82b7eec6cba3682374875d8f13407c7181ef0`, MIT (`LICENSE`). Checkout `<local-checkouts>/arbor` had the approved origin/HEAD and a clean tree. Current project source, tests, requirements and runtime behavior outrank this historical evidence.

## Question and scope

Following the [eviction study](bounded-scrollback-eviction.md): when a terminal enters and leaves an alternate screen, which state owns primary scrollback retention and the detached viewport? This pass examines Arbor's explicit mode projection and its consumers, then tests the analogous Heddlework VT/service boundary. It does not establish the internal alternate-buffer algorithm of Arbor's Alacritty dependency or native GUI behavior.

## Arbor entry, state and control flow

`crates/arbor-terminal-emulator/src/lib.rs:221-256` delegates bytes to the selected engine. For the default Alacritty path, `alacritty_emulator.rs:47-58` advances the processor against `Term`, increments generation and invalidates output/styled caches. `alacritty_support.rs:172-186`, `snapshot_modes` and `collect_styled_lines`, query the engine's current mode flags and grid separately: `TermMode::ALT_SCREEN` becomes `TerminalModes.alt_screen`; buffer allocation is not used as the mode signal in this wrapper.

`lib.rs:42-48,68-72` includes `modes` in `TerminalSnapshot` and defines the explicit `alt_screen` boolean. `alacritty_emulator.rs:96-117,133-146` packages modes with rows/cursor in full and tail snapshots. The wrapper leaves primary/alternate storage and retention to Alacritty; its default history configuration is supplied by `alacritty_support.rs:51-66`. Root `Cargo.toml:34` pins the dependency at `9d9640d4`. Its internal implementation was not inspected or acquired; a conventional Cargo registry-path lookup found no local match, which does not establish absence from every dependency cache.

`crates/arbor-gui/src/types.rs:1051-1064,1241-1280` exposes embedded snapshots to runtime consumers and applies changed generations to sessions. `terminal_interaction.rs:259-279`, `terminal_modes_for_session`, prefers the runtime snapshot's modes, falls back to stored session modes, and defaults if the session is missing. At :708-747, keydown gets those modes before encoding/writing. `terminal_keys.rs:113-145`, `to_esc_str`, emits Shift-Home/End/PageUp/PageDown escape sequences only when `modes.alt_screen` is true. This is a concrete production use of active-screen state, not merely unused snapshot metadata. Failed input writes set a notice; successful writes call the follow/input notification path.

The distinction is useful but does not prove detached-screen anchoring. `center_panel.rs:218-259` renders the snapshot through pixel-selected row ranges, and `terminal_rendering.rs:214-300` derives range/extent from content, cursor and selection. No explicit save/restore of a primary detached row anchor at an alternate-mode transition was found in this examined path. Do not infer it from the mode-aware key encoder.

## Direct tests and ownership limits

- `alacritty_emulator.rs:257-279`, `snapshot_modes_track_terminal_state`, feeds application-cursor enable, alternate-screen enable, and both disables. It checks mode values through the real wrapper. It does **not** append primary output after returning, assert history growth, or exercise a detached GUI viewport.
- `crates/arbor-gui/src/terminal_keys.rs:520-536`, `shift_navigation_uses_alt_screen_sequences`, passes synthetic modes and checks Shift-PageUp produces no bytes in default mode and `ESC[5;2~` in alternate mode. This proves the encoder branch, not runtime mode freshness or end-to-end delivery.

Upstream tests were read, not run. No direct detached-alt-entry/return-history regression was located in these modules. Alacritty's underlying storage/retention guarantees remain outside the source inspected here.

State and snapshots belong to the emulator/runtime, not an extra GUI parser. `terminal_backend.rs:340-368,428-457` owns PTY parsing, generation notification, EOF/read-error termination and poisoned-mutex recovery; :303-328 attempts process termination on close/last-owner drop. Input failure handling does not roll back a mode already parsed from output. No joining or native event-order guarantee is inferred from these paths.

## Heddlework comparison and behavioral evidence

`src/terminal/vt.ts:1229-1265`, `#setAltScreen`, routes modes 47/1047/1049 into buffer swapping. On enable it saves primary rows in `#alt`; on disable it swaps primary rows back but leaves `#alt` holding the alternate rows. `#scrollUp` (:1376-1383) pushes history only when `!this.#alt`. Thus allocated saved-buffer storage doubles as an active-mode predicate: after one return, primary output no longer enters history. `src/terminal/types.ts:52-65` does not expose an alternate-screen flag in `TerminalGridSnapshot`.

`vt.ts:325-358` always projects from shared history followed by the current screen at the requested offset. `src/terminal/service.ts:139-145,289-293` only adjusts offsets for retained-history growth; it has no mode transition branch. `src/ui/terminal-view.tsx:97-105` scrolls using that snapshot's offset. Explicit input resets the session to tail (`service.ts:192-201`), but output alone can switch modes while the session remains detached.

A read-only `bun -e` probe used the production VT and an injected production service backend, 16 columns × 3 rows:

1. Write `p0\r\np1\r\np2\r\np3`: history length is 1. Write `ESC[?1049hALT` then `ESC[?1049l`: primary row `p3` is restored. Append `\r\np4`: history remains **1**. A control VT receiving the same primary rows without the alternate round-trip has history **2**. This isolates the storage/mode conflation from cap eviction.
2. On a fresh service, write the initial four rows, detach at offset 1, then emit `ESC[?1049hALT`. The snapshot is **`p0,ALT,""`**, offset 1, cursor hidden: a primary-history row is mixed with the alternate screen. The mode switch was output-driven, without input resetting the offset.

Both characterization probes exited 0 and asserted the observed behavior; that is evidence of gaps, not acceptance of those behaviors. The service was disposed in `finally`, and listener detachment was asserted. `service.ts:235-257` owns timer/listener/process cleanup. No PTY or native UI was created.

`tests/terminal-vt.test.ts:165-170` asserts only that `main` returns after an alternate round-trip; it never appends enough output to scroll afterward. The detached-growth test at `tests/terminal-service.test.ts:181-195` never switches screens. Both full modules passed **24 tests / 95 assertions** in this round, despite the reproduced gaps. No app or test code changed.

## Disposition

**ADAPT.** Preserve Arbor's explicit, emulator-derived active-screen mode across the snapshot boundary instead of inferring it from saved-buffer existence. Heddlework needs separate active-mode and saved-storage state, plus an explicit policy for a primary detached anchor during alternate entry/exit. Arbor's mode flag and key test are useful evidence for that separation, not proof of a ready-made viewport policy or a transferred implementation.

## Retrieval and next question

Use for alternate-mode projection, saved-buffer ownership and primary-history resumption. Direct source navigation only; `heddlework-inspo-arbor` was not queried or refreshed. No dependency installation, upstream execution, remote update or reference mutation occurred. Freshness beyond the approved pin is unknown.

NEXT: when terminal selection/copy stores row coordinates, does prefix eviction or screen replacement rebase or invalidate them, or can a still-visible selection silently copy different text? That is a separate content-identity consumer worth inspecting in a later round. This round stops after two bounded questions.
