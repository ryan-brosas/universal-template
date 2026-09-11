<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# dsh-template: DeepSeek Harness Coding-Agent Template Foundation

## Use this for
Build a clonable DeepSeek Harness (DSH) coding-agent template or a DSH-native harness surface: a dependency-free `check.mjs` validation gate (surface, frontmatter, packs.json membership, foundation depth, profile layer, home templates, git diff, commit conventions), a `ctx.commands.register` command-plugin that turns `.dsh/prompts/<name>.md` files into slash-commands, a CDP browser-automation toolset (launch, navigate, content extraction, eval, element picker, HN scraper, cookies, screenshot), a profile patch layer (`cordis.patch.yml` + `dsh.profile.bundles`), `$DSH_HOME` config templates (`settings.yaml`/`mcp.yaml`), and DSH workflow orchestration. Source code is ground truth; references carry decisive excerpts and graph retrieval. There are no direct test files in the repo — every claim is source-grounded, and the coverage caveat is stated in each capsule.

## Load the matching source dump
- `./canonical-check.md` — the dependency-free DSH-template validation gate (`node scripts/check.mjs`).
- `./command-plugin.md` — turn `.dsh/prompts/*.md` files into DSH slash-commands via `ctx.commands.register`.
- `./browser-launch.md` — idempotent Chrome launch on :9222 with optional profile sync.
- `./browser-navigation.md` — navigate the active tab or open a new tab with reload, behind a 5s connect timeout.
- `./browser-content-extraction.md` — extract readable page content as markdown via CDP DOM + Readability + Turndown.
- `./browser-eval.md` — evaluate arbitrary JS in the page and format the result.
- `./browser-picker.md` — inject `window.pick()` for interactive element selection with a highlight overlay.
- `./browser-hn-scraper.md` — scrape Hacker News front-page submissions with cheerio.
- `./browser-cookies.md` — dump the active tab's cookies.
- `./browser-screenshot.md` — screenshot the active tab to a tmpdir PNG with a timestamp name.
- `./profile-patch-layer.md` — the DSH profile patch layer (`cordis.patch.yml` + `dsh.profile.bundles`).
- `./home-config-templates.md` — `$DSH_HOME` config templates (`settings.yaml` + `mcp.yaml`).
- `./workflow-orchestration.md` — the DSH `workflow` tool shape and parallel fan-out pattern.
- `./template-surface.md` — the DSH-native format-template surface mapped to DSH capabilities.
- `./memory-graph-cli-wrapper.md` — the `scripts/mgraph.mjs` thin CLI over `codebase-memory-mcp` with shell-free JSON args-files.
- `./ci-gate-double-run.md` — CI runs the validator twice: once as the strict failing gate, once under `always()` to append a one-line step summary.
- `./authoring-routing-gate.md` — check.mjs fails unless foundations-workflow routes authoring through writing-skills.
- `./commit-convention-gate.md` — unpushed-only conventional-commit subject + branch-name gate that never judges inherited history.
- `./goal-ledger-bootstrap.md` — the goals/ active-goal ledger with evidence-cited phase rows and the `[NEEDS CLARIFICATION]` anti-fabrication valve.
- `./agents-md-render-contract.md` — verified-only AGENTS.md authoring discipline (four legal claim types, one canonical completion command).
- `./prompt-registry-parity-gap.md` — the registered-but-missing `/verify` command: optimistic registration vs lazy per-invocation existence checks.
- `./prompt-porting-doctrine.md` — pi→DSH prompt porting table: durable markdown procedures × explicit host-surface mapping × cited wiring docs.
- `./profile-install-choreography.md` — profile install: copy the three patch-layer files → `pnpm install` in the profile dir → `dsh --profile`; bundles resolve dsh-installation-first, profile `node_modules` second.
- `./home-credential-boundary.md` — credentials live ONLY in `$DSH_HOME/.credentials.yaml` or env vars; committed templates carry `${VAR}` references that DSH expands.
- `./validator-layout-lag.md` — process guard: when the template layout migrates (root → `.dsh/*`), the validator's path constants must move in the same change or a pristine clone fails its own gate.

## Capsule map
- **Validation/CI** — `./canonical-check.md`: `check.mjs` dependency-free gate (no Pi remnants, AGENTS.md, skill frontmatter + packs.json membership, foundation depth, profile layer, home templates, workflows, `git diff --check`, commit conventions).
- **Command plugin** — `./command-plugin.md`: `project-prompts` plugin `apply`/`Config`/`resolveCommands`, `ctx.commands.register` handler that feeds the prompt body back to the agent via `invocation.agent.followup(createUserMessage(...))`.
- **Browser automation** — `./browser-launch.md` (`browser-start.js` idempotent :9222 launch + profile rsync), `./browser-navigation.md` (`browser-nav.js` last-tab/new-tab navigate + reload), `./browser-content-extraction.md` (`browser-content.js` CDP DOM → Readability → Turndown markdown), `./browser-eval.md` (`browser-eval.js` `page.evaluate` with `AsyncFunction`), `./browser-picker.md` (`browser-pick.js` `window.pick()` interactive picker), `./browser-hn-scraper.md` (`browser-hn-scraper.js` cheerio HN scraper), `./browser-cookies.md` (`browser-cookies.js` cookie dump), `./browser-screenshot.md` (`browser-screenshot.js` tmpdir PNG).
- **Profile/home wiring** — `./profile-patch-layer.md` (`cordis.patch.yml` YAML-array loader patch entries + `package.json` `dsh.profile.bundles`), `./home-config-templates.md` (`settings.yaml` agent presets + `mcp.yaml` MCP servers).
- **Orchestration/templates** — `./workflow-orchestration.md` (DSH `workflow` tool `meta`/`script`/`args` shape + parallel fan-out), `./template-surface.md` (DSH-native templates mapped to `schema_*`/`fabric_mesh`/`fovea_*` surfaces).
- **Graph-tooling** — `./memory-graph-cli-wrapper.md` (`mgraph.mjs`: five-verb reduction of codebase-memory-mcp; JSON options via `/tmp/mgraph-*.json` args-files so complex arguments never touch the shell).
- **Gates & CI** — `./ci-gate-double-run.md` (strict gate run + `if: always()` summary run ending `exit 0`; ref-scoped cancel-in-progress), `./authoring-routing-gate.md` (content-presence check forcing the authoring discipline into foundations-workflow), `./commit-convention-gate.md` (`origin/main..HEAD --no-merges` subject regex + `$GITHUB_HEAD_REF`-first branch gate; inherited history out of jurisdiction).
- **Agentic authoring contracts** — `./goal-ledger-bootstrap.md` (goal ledger = resume plan + evidence-cited progression + `[NEEDS CLARIFICATION]` valve), `./agents-md-render-contract.md` (verified-only claims, one canonical completion command, evidence per section).
- **Command-surface lessons** — `./prompt-registry-parity-gap.md` (`verify` registered but `verify.md` absent → deferred typed error; add registry↔disk parity checks), `./prompt-porting-doctrine.md` (porting table mapping procedures to host surfaces; research escalation ladder; ship stop-set).
- **Profile/home doctrine** — `./profile-install-choreography.md` (copy → profile-local `pnpm install` → `dsh --profile`; installation-first bundle resolution; edit `cordis.patch.yml`, never composed `cordis.yml`), `./home-credential-boundary.md` (two legal credential homes + `${VAR}`-placeholder-only committed templates).
- **Process guards** — `./validator-layout-lag.md` (clean-clone probe: validator path constants must migrate atomically with the template layout or the pristine pin fails its own gate 5×).

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Each new capsule must carry Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt, Flow, Invariant, a Probe, and a `search_graph` Retrieve.

## Provenance
dsh-template (no LICENSE file in repo, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory project `dsh-template` (FULL index: 11,167 nodes / 11,293 edges, generated 2026-08-23T00:32:26Z; pass-1 re-entry re-indexed the tree — the earlier fast-index 8,735/8,793 and its `scripts/` exclusion are OBSOLETE). Exclusions now: `.git`, `.idea`, `.pi` (by design). `scripts/check.mjs` + `scripts/mgraph.mjs` and the plugin symbols (`resolveCommands`, `apply`, `handler`) are graph-resident; all cited paths report `no_recorded_issue` + `metadata_match`. One parse_partial: a vendored mem0-foundation reference inside `.dsh/skills/` (template content, not machinery). No direct test files exist for the code — all claims are source-grounded, probes executed live at HEAD. PASS-2 ERRATUM (deep-rover re-entry): at this pin a PRISTINE clone of the committed tree FAILS `node scripts/check.mjs` (5 failures: root `profile/`, `home/`, `workflows/` checked but shipped under `.dsh/`) — the live checkout passes only via uncommitted worktree fixes; see `validator-layout-lag.md`.

## Full view (memory graph)
Revalidate `dsh-template` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source decides shipped claims. The graph is doc-shaped (8,958 Section / 22 Function nodes) — use symbol queries for code seams and text anchors for doctrine; `scripts/` is indexed since the full-mode re-index.

## Boundaries
Adopt the dependency-free canonical check gate, the `ctx.commands.register` command-plugin contract, the CDP browser-automation scripts, the profile patch layer, the `$DSH_HOME` config templates, and the workflow/template surfaces. Adapt the browser binary path, profile source dir, MCP server list, model/provider config, and prompt command set to the host. Omit the DSH agent-preset internals, the `fabric_mesh`/`schema_*`/`fovea_*` runtime behaviors (they live in the DSH harness, not this template), and the `vercel-deploy-claimable`/`find-polluter` scripts unless a target needs them.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agents-md-render-contract.md`](./agents-md-render-contract.md)
- [`authoring-routing-gate.md`](./authoring-routing-gate.md)
- [`browser-content-extraction.md`](./browser-content-extraction.md)
- [`browser-cookies.md`](./browser-cookies.md)
- [`browser-eval.md`](./browser-eval.md)
- [`browser-hn-scraper.md`](./browser-hn-scraper.md)
- [`browser-launch.md`](./browser-launch.md)
- [`browser-navigation.md`](./browser-navigation.md)
- [`browser-picker.md`](./browser-picker.md)
- [`browser-screenshot.md`](./browser-screenshot.md)
- [`canonical-check.md`](./canonical-check.md)
- [`ci-gate-double-run.md`](./ci-gate-double-run.md)
- [`command-plugin.md`](./command-plugin.md)
- [`commit-convention-gate.md`](./commit-convention-gate.md)
- [`goal-ledger-bootstrap.md`](./goal-ledger-bootstrap.md)
- [`home-config-templates.md`](./home-config-templates.md)
- [`home-credential-boundary.md`](./home-credential-boundary.md)
- [`memory-graph-cli-wrapper.md`](./memory-graph-cli-wrapper.md)
- [`profile-install-choreography.md`](./profile-install-choreography.md)
- [`profile-patch-layer.md`](./profile-patch-layer.md)
- [`prompt-porting-doctrine.md`](./prompt-porting-doctrine.md)
- [`prompt-registry-parity-gap.md`](./prompt-registry-parity-gap.md)
- [`template-surface.md`](./template-surface.md)
- [`validator-layout-lag.md`](./validator-layout-lag.md)
- [`workflow-orchestration.md`](./workflow-orchestration.md)
