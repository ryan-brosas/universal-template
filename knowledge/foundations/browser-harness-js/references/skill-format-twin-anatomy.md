<!-- capsule-v2 -->
# Skill-Format Twin Anatomy — SKILL.md as user manual, scripts/test as executable spec

## Source
Repo: browser-harness-js @ main`6b18940` (unchanged vs base_sha).

## Question
How are these skills authored so an agent can use them without reading the code — and how do they test themselves?

## Path / Symbol
- `skills/<name>/SKILL.md` (9 files; frontmatter `name/description/setup/compatibility`) + `scripts/<name>` + `scripts/setup` + `scripts/test`.
- Marketplace/plugin wiring: `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `skills/cdp/agents/openai.yaml` (agent-facing metadata for three host ecosystems).
- Learnings subsystem: `skills/cdp/learnings/README.md` + `example/{manifest.json, notes/, tools/get-outline.mjs}`.

## Data Shape
SKILL.md structure (consistent across all 9): keyless pitch → Commands with bash examples → arg tables → Result shapes with literal JSON examples → "How it works" table (data source × CDP technique) → "Why these sources" (source-selection rationale incl. rejected alternatives) → "Traps" (numbered gotchas written from reproduced incidents). findata's traps section alone carries 11 entries (YTD-cumulative quarters, sign normalization, duplicate period_end, ticker hyphen normalization, rate limits...).

## Decisive source
- gmaps SKILL.md frontmatter description enumerates all three modes + "Requires browser-harness-js on PATH and a running Chromium-based browser" — the description IS the router contract.
- findata SKILL.md "Why two capture strategies" documents the latency MEASUREMENTS behind code choices (~0.3s fetch path vs ~1.1s poll for companyfacts; Network.getResponseBody ~0.56s but "crashes the harness's WebSocket on multi-MB bodies") — rationale lives in docs when it can't live in code.
- scripts/test pattern (gmaps read whole, 112L): exit **77 = skip** when browser unreachable (`case "$probe" in *connect:*` probe call first), `expect`/`refuse` helpers over substring assertions, placeholder-leak checks (`refuse "__GMAPS_"`), deterministic guard tests that never touch the network ("Arg-count guards happen before any browser call, so they're deterministic").
- setup scripts: symlink CLI into `~/.local/bin`, append PATH to the first existing profile rc, then chain-link the cdp SDK dependency if missing.
- learnings/example manifest.json: per-site persistent-note schema (the repo's own extension point for site-specific knowledge).

## Flow / Invariant
The twin anatomy is the porting unit: a skill = manual-style SKILL.md + self-healing script + skip-capable smoke test + setup linker. Tests must degrade to skip (77), never false-fail, in headless environments.

## Probe (direct tests)
Structural probes at pin: all 8 data skills have scripts/test (findata/gmaps/gnews/gsearch/rsearch/xsearch/ttdl/ytdl) and scripts/setup; `grep -L "^setup:" skills/*/SKILL.md` → empty. The gmaps test's own header comment documents its exit-code contract verbatim.

## Retrieve
grep-first across `skills/*/SKILL.md`; graph Section nodes cover cdp/SKILL.md headings (313 Section nodes repo-wide).

## Verdict
ADOPT as the template for authoring new CDP data skills; copy the trap-documentation discipline (reproduced incident → numbered trap entry).
