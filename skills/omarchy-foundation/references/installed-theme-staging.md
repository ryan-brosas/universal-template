# How does installed-theme staging reject symlinks and constrain legacy extraction?

Source: [basecamp/omarchy](https://github.com/basecamp/omarchy) at
`a9eaf7978e33a6832630c51f1bb87f97dbf5fe36`, MIT. Historical source evidence.
Checkout: `<local-checkouts>/omarchy`; origin and approved HEAD matched and
`git status --porcelain` was empty before study. No remote update or checkout change.

## Question and execution path

Can an installed theme make staging follow nested symlinks or carry its terminal
launch configuration through legacy palette recovery?

- `bin/omarchy-theme-set:283-318`: validate the normalized name, lock fd 9, remove
  and recreate `next-theme`, copy official files, then overlay user material.
- `theme_came_from_a_repo`, :239-243, selects filtering only for a non-symlink
  source with a `.git` directory. A hand-written directory or symlinked working
  copy takes the unfiltered `cp -r` branch (:310-311). This is a trust convention,
  not verification of origin; a `.git` file is not the tested directory condition.
- `is_denied_installed_file`, :173-184, rejects case-sensitive `*.lua` and the
  exact terminal/extension filenames listed at :30. `stage_installed_theme`,
  :245-268, checks each top-level entry before copying; symlinks are skipped.
- `stage_installed_dir`, :215-232, walks `"$source"/*` and tests `-e && ! -L`
  BEFORE `-d` or `cp`. Each recursive invocation repeats this test, so ordinary
  stable nested file/directory links are skipped rather than followed. Dotfiles
  are omitted by the normal shell glob, including `.git` at the top level.
- `stage_installed_colors_from_alacritty`, :189-210, returns if staging already
  has `colors.toml`; otherwise accepts only a regular, non-symlink source
  `alacritty.toml`. It copies that file to a fresh scratch directory, invokes
  `omarchy-theme-colors-from-alacritty` there, copies back only `colors.toml` if
  present, and removes scratch. The terminal configuration itself stays out of
  staging. Official palette presence can therefore suppress legacy overlay extraction.

## Invariants, counterevidence and cleanup

The recursion rejects links; it does NOT recursively apply the filename denylist.
For example the hostile fixture writes `backgrounds/payload.sh` and the directory
copy path permits ordinary nested files. The source comment that everything else
is color is policy, not proof about arbitrary consumers. Top-level filtering is
not a general sandbox, recursive extension allowlist, file-size limit or depth bound.

Checks precede pathname operations; no descriptor-relative no-follow open protects
against concurrent replacement between check and copy. No race test was located.
Official themes and user-authored/symlinked roots deliberately bypass this filter.
Scratch removal is sequential, not an EXIT trap. The caller lacks `set -e` and does
not branch on copy/extractor failure. Missing extraction output is tolerated;
there is no demonstrated transactional rollback on failure or signal. The writer
later removes/moves active state (:337-341) and unlocks (:361); the existing
[reader-boundary capsule](staged-theme-reader-boundary.md) owns that distinct seam.

## Direct test evidence, inspected only

`test/shell.d/theme-staging-test.sh:22-27` invokes the PRODUCTION theme-set script
in a temporary HOME with headless/background-skipping flags, not a test-only
reimplementation. Its temporary-home EXIT trap is at :12-13, not production cleanup.

- :68-120 builds the hostile repository fixture and asserts retained colors,
  denied executable configuration replaced by generated templates, omission of
  a top-level `/etc/hostname` link and `.git`, and ignored-file reporting.
- :122-132 directly asserts refusal of a symlinked top-level `icons.theme`.
- :134-162 asserts legacy palette recovery and absence of the launch marker in
  the generated Alacritty config. It does not assert a shell payload was executed
  or sandboxed; it checks staged contents.
- :164-205 covers stock overlays, unfiltered personal/symlinked roots and rejected
  traversal names. :207-229 classifies built-in generated template names; this
  does not enumerate every file a theme could ship.

No direct nested-link, symlinked legacy input, check/copy race, scratch interruption,
FIFO/depth exhaustion or failing-extractor assertion was found in this test.
No upstream script or test was executed; no setup/dependency installation occurred.

## Heddlework comparison and disposition

`src/main.tsx:46-51` opts Linux into an Omarchy palette reader; :97 and :176 attach
its dispose/start lifecycle. `src/ui/theme-manager.ts:219-226` reads text (default
read errors become undefined), never stages themes or launches an Omarchy script.
`src/ui/theme.ts:119-165` recognizes a small semantic field set and validates hex
values. `ThemeManager.dispose`, :113-122, withdraws effects in reverse order;
watcher closure is idempotent at :183-205. Reading one local file can follow a
symlink, but it neither recursively copies assets nor evaluates a theme config.
The legacy XDG_CONFIG_HOME path at :258-261 still differs from this upstream pin.

**Disposition: ADAPT.** Preserve the data-only palette boundary rather than importing
Omarchy's provenance heuristic or shell staging. If Heddlework later imports theme
bundles, specify and test its own nested-entry/race/resource policy; this upstream
check-before-copy implementation is not sufficient proof of hostile-filesystem safety.

Verification: `bun test ./tests/theme-omarchy.test.ts` passed 11 tests / 25 assertions
(exit 0). Those parser and injected event-source tests establish local reading and
cleanup behavior, not hostile upstream staging or live desktop behavior. No app or
test code changed. Direct source navigation was used; no source graph was queried
or reindexed, and graph coverage is not claimed.

Next question: what exact legacy palette grammar, precedence and missing-color
behavior survives extraction, and how does it differ from Heddlework's reader?
See [the follow-up capsule](legacy-palette-contract.md).
