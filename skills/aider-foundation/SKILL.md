---
name: aider-foundation
description: "Use when building AI pair-programming harnesses: token-bounded repository context, repairable edits, explicit file and consent gates, plan-to-edit handoff, diagnostic feedback, provider policy, and scoped Git safety."
disable-model-invocation: true
---
# Aider: AI Pair-Programming Foundation

## Use this for
Build or harden an AI coding harness that selects repository context under a token budget, turns plans into guarded edits, returns actionable repair diagnostics, and preserves user-controlled consent, retry, and Git boundaries. Aider source and direct tests are ground truth; the capsules carry decisive excerpts and live graph retrieval.

## Load the matching source dump
- `references/repomap.md` — PageRank-ranked tags, chat-file exclusion, and token-budget fitting.
- `references/context-orchestration.md` — fixed prompt ordering and tail-preserving history reduction.
- `references/summary-fallback.md` — ordered summarizer fallback with a normalized history result.
- `references/edit-formats.md` — SEARCH/REPLACE matching ladder and loud repair failure loop.
- `references/edit-admission.md` — registered format dispatch, transcript sanitation on a mode switch, and per-target edit consent.
- `references/git-safety.md` — dirty baselines and edited-path-only commits.
- `references/undo.md` — git-backed unwind of only the last aider-owned, unpushed commit.
- `references/commit-attribution-matrix.md` — explicit-over-implicit author/committer/co-author algebra applied by restore-on-failure env swaps.
- `references/commit-message-model-ladder.md` — weak-model commit-message fallback that skips over-budget models and strips only matched quote pairs.
- `references/empty-repo-diff-selection.md` — HEAD-diff vs index+worktree split chosen by branch-commit presence, with untracked-path annotations.
- `references/diagnostic-feedback.md` — preserved failing output with line-scoped structural context before model reflection.
- `references/linter-language-dispatch.md` — four-rung per-language dispatch (callable > shell > tree-sitter) merging parallel diagnostics by unioned lines.
- `references/command-reflection-dispatch.md` — reflection-as-registry command table with exact-over-prefix resolution and per-dispatch git-failure containment.
- `references/file-add-admission-machine.md` — two-stage `/add` admission: tracked-only glob expansion, then consent gates including repo-proof read-only promotion.
- `references/token-window-report.md` — context-window decomposition rows, image tile pricing, three-way remaining ladder, fail-open token counting.
- `references/coder-preflight-plane.md` — format_messages→check_tokens→warm_cache ordering where the budget gate asks consent instead of vetoing, and only primary coders warm prompt caches.
- `references/collab.md` — AI-comment watch routing and bounded lint/edit reflection.
- `references/reply-driving-pipeline.md` — one choke point ordering retries, exhaustion, prefill continuation, interrupts, edits, commits, lint, shell, and tests into at most one reflection per turn.
- `references/file-mention-auto-add-gate.md` — separator-bearing unique-basename mention grammar with session-sticky refusals.
- `references/architect-handoff.md` — consent-gated plan-to-editor transfer in an isolated edit session.
- `references/ux.md` — grouped confirmation preference, explicit-yes protection, and multiline restoration.
- `references/model-policy.md` — exact-over-generic settings, deep overrides, and capped retry recovery.
- `references/model-info-cache-ladder.md` — local json5 overrides > 24h disk cache > litellm-only-if-needed > vendor scrape, never forcing the heavy import.
- `references/model-settings-splice.md` — slice-splice replace-by-name registration preserving list identity, with the `aider/extra_params` wildcard overlay and identity-deduped sanity trio.
- `references/shell-output-consent.md` — explicit run approval and separate chat admission.
- `references/relative-indent-transform.md` — pairwise delta-indent encoding with outdent markers and identity roundtrip.
- `references/flexible-strategy-engine.md` — ordered exact→git-cherry-pick→line-DMP ladder where every rung is all-or-nothing.
- `references/dmp-line-mode-patching.md` — line-unitized diff_match_patch with tight anchor knobs and shared sentinel mapping.
- `references/line-pad-unpad.md` — 100-newline moat that turns appends/creates into plain substring matches.
- `references/udiff-partial-hunk-ladder.md` — dedupe+normalize then context-shrinking hunk application with tiny-anchor refusal.
- `references/udiff-fence-parser.md` — ```diff fence grammar with sticky paths, keeper gate, and git-prefix stripping.
- `references/v4a-patch-parser.md` — Begin-Patch sentinel tolerance, action merge matrix, and pre-parse file staging.
- `references/patch-context-finder.md` — exact→rstrip→strip fuzz tiers with EOF anchoring and a +10,000 penalty.
- `references/patch-chunk-applier.md` — index-absolute chunk splice with delete-line re-verification and move-after-write.
- `references/streaming-markdown-window.md` — stable-lines-to-scrollback vs live-repainted tail with render-time adaptive throttle.
- `references/history-markdown-splitter.md` — `#### `/`> ` marker grammar rebuilding an ordered message list from chat markdown.
- `references/versioned-help-rag-cache.md` — per-version RAG cache over packaged docs with corrupt-rmtree rebuild and URL-reconstructing metadata.
- `references/parser-projected-docs.md` — HelpFormatter subclasses that render .env/YAML/markdown artifacts from the live parser so samples cannot drift.
- `references/tty-shell-runner.md` — TTY-gated pexpect passthrough vs never-raise subprocess capture.
- `references/tempdir-and-installer.md` — cleanup-tolerant temp-dir wrappers plus probe→consent→install→re-probe loop.
- `references/triple-parse-config-bootstrap.md` — CWD→git-root→home config ladder with wrong-repo restart and .env reparse.
- `references/switchcoder-repl.md` — exception-as-control-flow coder hot-swap with one-shot swallow sites.
- `references/slow-import-split.md` — installs.json first-run gate choosing sync-fail vs background-thread imports.
- `references/git-bootstrap-ladder.md` — consent-gated repo init, identity backfill, and .gitignore self-protection.
- `references/repo-sanity-gate.md` — tracked-files probe with index-version / path-encoding / corrupt triage.
- `references/batch-mode-ladder.md` — ordered --lint/--test/--commit/--message/--apply early-exit matrix.
- `references/onboarding-model-ladder.md` — env-key scan → default pick → OpenRouter OAuth with oauth-keys.env round-trip.
- `references/message-alternation-guard.md` — strict alternation validator vs lenient empty-turn repair.
- `references/litellm-exception-taxonomy.md` — closed-world retry table with strict drift check and str(ex) sub-cases.
- `references/reasoning-tag-scrubber.md` — DOTALL pair removal plus closing-tag salvage for truncated streams.
- `references/analytics-percentage-sampling.md` — first-6-hex UUID threshold sampler with permanent opt-out persistence.
- `references/versioncheck-upgrade-ladder.md` — PyPI check throttled fail-open with interpreter-path-derived upgrade commands.
- `references/crash-report-consent-gate.md` — excepthook chaining plus consent-first, browser-mediated issue reporting.
- `references/log-scrub-settings-formatter.md` — last-4 key mask across argv echo and settings dumps.
- `references/ssl-verify-optout-shim.md` — force-load litellm then swap sync+async httpx sessions for --no-verify-ssl.
- `references/deprecated-model-shims.md` — mirrored flag/handler tables with alias-aware deprecation warnings.
- `references/cli-arg-surface-census.md` — 945-line configargparse trinity (flag≡env≡yaml) with derived edit-format choices.
- `references/prompt-scaffold-grammar.md` — CoderPrompts attribute vocabulary plus the lazy/over-eager leash pair.
- `references/copypaste-format-promotion.md` — clipboard mode promotes diff/whole formats to editor twins only when unpinned.
- `references/gui-launch-shim.md` — streamlit launch with credentials pre-seed and dev/release flag fork.
- `references/waiting-spinner-contract.md` — 0.5s-delayed, padding-corrected terminal spinner with truncation-safe backspaces.
- `references/wholefile-fname-precedence.md` — block>saw>chat filename resolution with bogus-dir collapse (#1232 guard).
- `references/function-call-edit-contract.md` — replace_lines schema, list/string coercion, and the RuntimeError tombstone twin.
- `references/context-coder-convergence.md` — file-selection agent as reflection loop over mention-set equality.
- `references/root-important-files-census.md` — basename-at-any-depth manifest with .github/workflows carve-out.
- `references/coder-family-registry.md` — __all__ as the registry feeding factory dispatch and argparse choices.
- `references/partial-diff-live-preview.md` — last-common-line truncation with progress bar and fence escape.

## Capsule map
Each capsule pairs decisive evidence, a preserved invariant, a direct-test probe, and a live `search_graph` retrieval. The map records portable seams, not a source census.

- **Context selection and assembly** — `references/repomap.md`, `references/context-orchestration.md`, `references/summary-fallback.md`: budget repository context, preserve the active turn while compressing archival history, and recover summarization through ordered model fallback without admitting a partial result.
- **Edit protocol and mutation boundary** — `references/edit-formats.md`, `references/edit-admission.md`, `references/git-safety.md`, `references/undo.md`, `references/diagnostic-feedback.md`, `references/linter-language-dispatch.md`: select a compatible format, ask before expanding scope, reject unsafe matches, keep a reversible baseline, revert only the last aider-owned unpushed commit, and route per-language lint diagnostics into compact feedback for the model.
- **Commit attribution & messaging** — `references/commit-attribution-matrix.md`, `references/commit-message-model-ladder.md`, `references/empty-repo-diff-selection.md`: blame AI edits through an explicit-over-implicit attribution table with restore-on-failure identity swaps, generate messages via a token-budgeted weak-model ladder, and select HEAD-vs-index+worktree diffs that survive empty and detached repos.
- **Drift-tolerant edit engines** — `references/relative-indent-transform.md`, `references/flexible-strategy-engine.md`, `references/dmp-line-mode-patching.md`, `references/line-pad-unpad.md`: match edits under indentation and content drift through an ordered all-or-nothing strategy ladder with a relative-indent preproc.
- **Unified-diff plane** — `references/udiff-fence-parser.md`, `references/udiff-partial-hunk-ladder.md`: parse fenced diffs with sticky paths, then apply hunks through normalization, sectioning, and a context-shrinking ladder that refuses ambiguous micro-anchors.
- **V4A patch plane** — `references/v4a-patch-parser.md`, `references/patch-context-finder.md`, `references/patch-chunk-applier.md`: tolerate missing sentinels, quantify context-matching fuzz while applying anyway, and verify delete lines again at apply time before any move-after-write.
- **Streaming presentation and session replay** — `references/streaming-markdown-window.md`, `references/history-markdown-splitter.md`: repaint only the volatile tail of streamed markdown, and rebuild structured messages from exported chat markdown.
- **Collaboration and consent** — `references/collab.md`, `references/architect-handoff.md`, `references/ux.md`: bound reflection, turn a reviewed plan into a separate edit pass, and never weaken explicit consent.
- **Reply pipeline & file admission** — `references/reply-driving-pipeline.md`, `references/coder-preflight-plane.md`, `references/file-mention-auto-add-gate.md`: order preflight and post-reply side effects so the budget gate asks instead of vetoing, every failure class becomes at most one reflection with an alternation-valid transcript, and auto-add mentioned files only on separator-bearing unique basenames with refusals remembered.
- **Provider policy and recovery** — `references/model-policy.md`, `references/model-info-cache-ladder.md`, `references/model-settings-splice.md`: exact policy wins; user overrides merge deliberately; retry terminates at its time bound; model metadata resolves local-first without forcing heavy imports or offline-breaking network calls; late settings replace by name through slice assignment so existing importers stay live.
- **Command console & observability** — `references/command-reflection-dispatch.md`, `references/token-window-report.md`, `references/versioned-help-rag-cache.md`, `references/parser-projected-docs.md`: reflect commands from method names with exact-over-prefix resolution, report context usage as decomposed fail-open rows, cache help RAG per version with corrupt-rebuild recovery, and project config docs from the live parser so samples cannot drift.
- **Command execution boundary** — `references/shell-output-consent.md`, `references/tty-shell-runner.md`: require explicit consent before running model-suggested shell commands, keep a separate consent before their output enters chat context, and always capture exit status plus output whether the run is interactive or headless.
- **Test-infra and dependency self-install** — `references/tempdir-and-installer.md`: tolerate hostile cleanup of throwaway git/chdir workspaces, and never install dependencies without a consent gate plus a re-import verification.
- **CLI composition root** — `references/triple-parse-config-bootstrap.md`, `references/switchcoder-repl.md`, `references/slow-import-split.md`, `references/batch-mode-ladder.md`, `references/cli-arg-surface-census.md`: bootstrap config through a git-root-correcting triple parse, hot-swap coders by exception, split heavy imports on a first-run ledger, keep batch flags out of the REPL, and declare options once for flag/env/yaml.
- **Repo & identity bootstrap** — `references/git-bootstrap-ladder.md`, `references/repo-sanity-gate.md`, `references/onboarding-model-ladder.md`, `references/deprecated-model-shims.md`: consent-gate every repo mutation, triage index/encoding failures with remediation, fall back from env keys to OAuth, and keep legacy model shims warning-first.
- **Provider error & stream hygiene** — `references/message-alternation-guard.md`, `references/litellm-exception-taxonomy.md`, `references/reasoning-tag-scrubber.md`, `references/ssl-verify-optout-shim.md`: validate then repair message alternation, classify provider errors against a closed-world table, scrub hidden reasoning even from truncated streams, and cover every session when weakening TLS.
- **Telemetry & lifecycle consent** — `references/analytics-percentage-sampling.md`, `references/versioncheck-upgrade-ladder.md`, `references/crash-report-consent-gate.md`, `references/log-scrub-settings-formatter.md`: sample cohorts deterministically, throttle update checks fail-open, report crashes only via user-driven browser flow, and mask secrets in every log surface.
- **Coder family & prompt plane** — `references/coder-family-registry.md`, `references/prompt-scaffold-grammar.md`, `references/context-coder-convergence.md`, `references/copypaste-format-promotion.md`, `references/gui-launch-shim.md`, `references/waiting-spinner-contract.md`: derive format choices from the class registry, treat prompts as a named-attribute API, reuse reflection for file selection, promote formats only when unpinned, embed streamlit without first-run prompts, and render spinners that never corrupt the line.
- **Whole-file & function-call editors** — `references/wholefile-fname-precedence.md`, `references/function-call-edit-contract.md`, `references/partial-diff-live-preview.md`, `references/root-important-files-census.md`: resolve fenced filenames by source reliability, coerce tool-call line arrays defensively, preview streaming rewrites without phantom deletions, and boost structurally important files in repo maps.

## Extending the foundation
Add one graph-selected, source-confirmed capsule per new portable seam. Add exactly one loader line and one grouped map reference; retain decisive source, an invariant, a direct-test probe, and a `search_graph` retrieval in the capsule rather than expanding this leaf.

## Provenance
Aider (Apache-2.0), `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index: 7,507 nodes / 19,923 edges, re-verified 2026-08-24 at unchanged HEAD — base_sha equals head_sha, origin fetch 0-behind, zero drift; registered root `inspo/aider` is a LIVE SYMLINK into `coding-agents/aider`, readlink-verified benign per the linkedin-suite precedent). Parse-partial tree/site/fixture ranges and 74 intentionally excluded non-code assets are a best-effort coverage caveat; source and direct tests remain authoritative. Pass 2 (2026-08-23 deep rover): citation-vs-inventory sweep mined the never-cited edit-engine planes (`search_replace.py`, `udiff_coder.py`, `patch_coder.py`) plus `mdstream.py`, `utils.py`, and `run_cmd.py`. Pass 3 (2026-08-24 deep-rover second worker): executed queued target #1 again at the same pin — file-granular census over 81 package files exposed ~60 never-cited modules → mined the CLI composition root (`main.py` 1274L whole-file), config/args plane, sendchat/exceptions/reasoning infra, wholefile + function-call coder variants, diffs/special/analytics/waiting utils, and onboarding/report/versioncheck lifecycle planes; gate-5 REAL RUNNER installed pytest via uv and executed 10 suites green (157 passed + 55 subtests), with per-capsule deterministic probes executed byte-exact BEFORE writing (8 expectation corrections caught live: ExInfo=27, fname_source=11, last_non_deleted=11, backticks=:87, backspaces=5, patterns_to_add=8, SwitchCoder sites=2, compute_hex=:51). RECORD REPAIR: pass 4's work-record notes claimed a commands/help/editor/llm capsule batch, but no such reference files or loader lines exist on disk — only its learning notes persisted; those seams are queued for pass 6 and remain uncited. Pass 5 (2026-08-25 deep-learning pass, same pin): mined the recorded NEXT-PASS TARGETS — repo.py attribution matrix / weak-model message ladder / empty-repo diff selection (the abs_read_path/abs_write_path target was VOID at this pin: symbols absent from source AND graph), models.py model-info cache ladder with registration deferral, base_coder.py reply-driving pipeline + file-mention gate, linter.py language dispatch; direct suites green in repo .venv Python 3.11.16 (test_repo+test_model_info_manager+test_linter = 30 passed/1 skipped; test_coder -k file_mentions = 5 passed + 17 subtests; test_sendchat = 12 passed); repaired collab.md corrupted pin hash and corrected the leaf-wide wrong license claim (48 refs said MIT; LICENSE.txt is Apache-2.0). Pass 6 (2026-08-25 deep-learning pass, same pin, graph re-verified head==base==pin): mined the pass-4 phantom batch for real — commands.py reflection dispatch (43 cmd_ methods), /add admission state machine (tracked-only glob filter + repo-proof read-only promotion), /tokens window decomposition (+ OpenAI image tile math 2048/768/512×170+85), args_formatter.py parser-projected docs, help.py version-keyed RAG cache with corrupt-rmtree rebuild; plus models.py settings splice (MODEL_SETTINGS[:] replace-by-name, aider/extra_params wildcard) and base_coder preflight plane (format_messages→check_tokens→warm_cache); refactored slow-import-split.md to fold in the llm.py LazyLiteLLM proxy. Direct tests green: test_commands -k 'test_cmd_add or test_cmd_tokens_output or save_and_load' = 26 passed; test_models -k 'extra or sanity or register' + test_help fname_to_url trio = 6 passed. BLOCKER CORRECTED: tests/help/test_help.py EXISTS (the old blocker named only tests/basic/test_help.py).

## Full view (memory graph)
Revalidate `aider` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; Aider source and direct tests decide shipped claims. Pass-3 retrieval note: single-symbol BM25 queries resolve rank-1 line-exact for all new seams (`generate_search_path_list`, `ensure_alternating_roles`, `find_last_non_deleted`, `compute_hex_threshold`, …); multi-word prose queries can return total:0 — fall back to a symbol from the capsule's Path/Symbol header. Pass-5 note: `abs_read_path`/`abs_write_path` are NOT graph nodes at this pin (name_pattern search total:0) because they do not exist in source either — cite repo.py path handling via `abs_root_path` only.

## Boundaries
Adopt context selection, guarded edit admission, repair feedback, drift-tolerant edit application (relative-indent preproc, strategy ladders, fuzz-accounted context matching), diagnostic reflection, consent, bounded retry, scoped mutation contracts, consent-gated repo/gitignore mutation, closed-world provider-error classification, reasoning-tag scrubbing with closing-tag salvage, and deterministic telemetry sampling. Adapt model-provider dialects, editor/watch transports, host Git integration, OAuth provider tables, PyPI upgrade commands, and analytics vendors. Omit Aider CLI/prompt wording (beyond the leash-pair invariants), UI styling, scraping, voice, and commit-message generation unless a target requirement needs them. Known latent traps: the fuzzy `replace_closest_edit_distance` in `editblock_coder.py` sits below an unconditional return (dead code — do not "fix" into a default-on fuzzy matcher); character-level `dmp_apply` offsets are wrong for drifted originals without `map_patches` remapping (benchmark-only path); `EditBlockFunctionCoder.__init__` raises RuntimeError by design (schema/coercion lessons stand, instantiation does not); `diff_partial_update` returns EMPTY when streamed content shares no line with the original — that guard is load-bearing, not a bug.
