# What survives legacy Alacritty palette extraction?

Source: [basecamp/omarchy](https://github.com/basecamp/omarchy) at
`a9eaf7978e33a6832630c51f1bb87f97dbf5fe36`, MIT. Historical evidence, not a
strict TOML specification. Origin, HEAD and clean checkout were rechecked locally.

## Question and entry boundary

Which grammar, precedence and missing-color rules produce `colors.toml`, and does
Heddlework share them? This follows the [installed staging study](installed-theme-staging.md),
which owns symlink rejection and scratch cleanup.

`bin/omarchy-theme-set:189-210` invokes the extractor on an isolated scratch copy
for filtered installed themes, copying back only generated colors. The general
fallback at :314-317 instead invokes it on staging when colors are missing and
Alacritty configuration exists. These are different trust boundaries.

`bin/omarchy-theme-colors-from-alacritty:7-26` enables `set -e`, requires a theme
directory argument, skips existing output, and skips absent input. It parses the
input as text using AWK (:36-87), never sourcing terminal configuration. It emits
a fixed output schema (:128-151), not arbitrary input keys or terminal settings.

## Grammar and invariants from production source

- :39-48 recognizes a section only when the complete header ends after `]` and
  optional horizontal whitespace. A header with a trailing comment clears section
  state. Top-level assignments before a section are ignored. This is a narrow
  line parser, not a TOML implementation.
- :50-73 splits at the first equals sign and accepts six hexadecimal digits, with
  optional prefixes/quotes according to its regex, then lowercases and emits `#`.
  Quoted input can use `#`, `0x` or `0X`; bare input accepts lowercase `0x` or no
  prefix, not bare `#`. Eight-digit alpha colors are rejected.
- The regex at :68 makes the closing quote optional and does not require matching
  quote kinds. Thus an opening quote plus six valid digits can pass without a
  closing quote. This source-level counterexample means “validated color” does
  not imply valid TOML. The emitted value is still normalized hex. Not executed.
- :75-85 stores first valid occurrences separately for direct section keys and
  dotted keys under `[colors]`. A direct `colors.normal.black` wins over its
  dotted form regardless of encounter order. Invalid values never enter either
  table. Arbitrary paths can enter the internal map, but only fixed color paths
  are selected for output.
- :89-103 requires all eight normal colors. Any missing normal color prints a
  warning and exits **0 without generating output**. Exit success alone is not
  evidence of extraction success.
- :105-124 fills bright colors from their corresponding normal colors FIRST;
  afterward primary background/foreground default to normal black/white and
  replace `color0`/`color7`. Consequently absent bright black/white can retain the
  original normal values even when primary overrides change `color0`/`color7`.
  Selection defaults to final foreground; accent is normal blue (`color4`).
- :128-151 writes only accent, selection, background, foreground and color0-15.
  It does not recover `mode`, `muted`, editor extensions or terminal launch commands.

## Failure and cleanup ownership

Output uses direct redirection, not a temporary-file rename. `set -e` is not an
atomic-output guarantee; AWK runs in process substitution and its status is not
explicitly checked. Missing normal colors are intentionally a successful no-op.
The staging caller checks output existence, not command status or schema, and
removes scratch sequentially without an EXIT trap. The standalone extractor owns
no cleanup trap. No crash-safe rollback or complete malformed-input rejection is
established. `bin/omarchy-theme-set-templates:371-405` generates files only when
colors exist and leaves existing config files in place; it is downstream behavior,
not proof the extractor always produces output.

## Direct tests and missing coverage

`test/shell.d/theme-staging-test.sh:134-162` supplies all eight normal colors plus
primary background/foreground and a terminal-shell marker. Through its production
headless `set_theme` invocation (:22-27), it asserts recovered `#102030`, presence
of colors and absence of the marker in staged Alacritty configuration. These are
content assertions, not execution detection or a grammar matrix.

The direct test was inspected, not run. A filename search for Alacritty tests and
bounded content search for `colors-from-alacritty`, `dotted`, and `normal colors`
under upstream `test/` found no dedicated extractor tests. This is a located-test
gap, not proof none exist elsewhere. No direct assertions were found for duplicate
precedence, section comments, unmatched quotes, missing normals, bright-before-
primary fallback or interrupted output. No Omarchy script, setup or test executed.

## Heddlework comparison

`src/ui/theme.ts:119-165`, `parseOmarchyPalette`, consumes already generated
semantic colors rather than Alacritty input. It differs deliberately or accidentally:

- Six/eight-digit `#` values are accepted; six-digit-only extraction is not its API.
- Section headers are skipped without tracking a section, so recognized fields
  beneath unrelated sections are consumed. Later assignments replace earlier
  ones before validation, including invalid later values.
- It accepts partial semantic overlays; normal-color completeness is not required.
  Although the nearby comment mentions ANSI slots, the actual mapping uses only
  semantic fields/aliases and does not map `color0`-`color15` or `mode`.
- `applyResolvedTheme` (:107-112) starts from built-in colors on each application.
  `ThemeManager.refreshSystemTheme` (`src/ui/theme-manager.ts:102-111`) detects
  content-key changes; default missing/read-error input (:218-225) removes the
  overlay, rather than retaining last-good colors. Watcher/polling ownership and
  reverse cleanup (:93-132, :183-205) remain in the manager; no extractor is spawned.

**Disposition: ADAPT.** Keep the fixed, data-only semantic consumer rather than
copying legacy grammar or requiring a complete ANSI palette. Treat duplicate and
section handling as explicit local compatibility decisions, with dedicated tests
if relied upon; upstream acceptance is not Heddlework's parser contract.

## Verification and next question

`bun test ./tests/theme-omarchy.test.ts`: exit 0, 11 tests and 25 assertions. Tests
cover semantic mapping, malformed/non-hex input and injected watcher/poll lifecycle,
not the upstream parser edge cases above.

A one-off `bun -e` probe imported the production Heddlework parser/manager and used
injected reads, watcher and process hooks (no application/test file changes). Nine
assertions passed: alpha accepted; invalid duplicate removes a field; unrelated
section does not hide a field; ANSI-only input yields no overlay; unmatched quote
is rejected; initial palette applied; missing read resets built-ins; later content
recovers; double dispose closes the watcher once. Its success message incorrectly
said eight assertions; the actual call count is nine. No live desktop, upstream
execution or native watcher rebinding is proved. No source graph was queried.

NEXT: how does upstream `omarchy-theme-color` resolve semantic aliases, defaults
and malformed values in modern `colors.toml`, and which subset should Heddlework
recognize? Deferred to the next round: two bounded questions are complete here.
