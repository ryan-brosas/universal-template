<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# OpenOutreach: GP-Qualified Lead Finder Foundation

## Use this for
Use when building a browserless lead finder or any funnel that discovers candidates, qualifies them with an LLM + Gaussian-process active-learning loop, ranks them behind a spend gate, buys an enrichment through an async two-step provider handshake, and exports rows for another tool to act on. Also for queue-as-status designs (work found by querying rows, never pre-created), goal-bounded batch jobs with typed stop reasons, and cooperative email caches with jurisdiction gates. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./cycle-priority-rows.md` — one action = walk an ordered ROWS tuple; spending is opt-in per call.
- `./job-goal-bounded-run.md` — progress as a set delta; emails goals cap new paid submissions by presented-set arithmetic.
- `./lookup-two-step-waterfall.md` — free sources first, paid submit parks the deal on its handle; backoff uncapped.
- `./bettercontact-async-split.md` — submit/poll_once split vs blocking submit_and_poll; 429s backed off in urllib3, refusals typed at the HTTP boundary.
- `./hub-give-to-get-store.md` — resolve-before-pay, contribute-after-hit; identity ≠ entitlement; EEA gates client-side and server-side.
- `./discovery-empty-semantics.md` — empty pages are four different facts; positive-count-empty-page is a transport artifact, never retired.
- `./select-frontier-beta-smoothing.md` — Laplace budget pointed at the parent's rate; Thompson draws from the same Beta; global frontier, no remove move.
- `./select-retirement-prune.md` — dead/drained/capped retirement keyed on offset; anti-monotone dead-set check at creation covers DAG supersets.
- `./labelstore-anchor-positives.md` — anchors counted as positives break the cold-start closed loop; children must co-occur in a qualified profile.
- `./vocabulary-counted-growth.md` — df≥2 admission over qualified profiles; token field measured by source row fields, never chosen.
- `./icp-seed-vocabulary.md` — the LLM writes words, not queries; every value split into tokens; anchors are permanent invented positives.
- `./qualifier-gp-bald.md` — GPR (not GPC) posterior; P(f>0.5) via norm.sf; BALD by MC probit sampling; lazy refit with O(n³) honesty.
- `./qualifier-acquisition-phases.md` — cold phase forces exploit because BALD picks accurate rejections; balance drives explore/exploit after ANCHOR_COUNT real positives.
- `./ready-pool-spend-gate.md` — min_gp_confidence is the paid-lookup gate and nothing else; unchanged pools are never refitted.
- `./export-importer-contract.md` — columns named by importers; both rejection classes excluded; no score column, deliberately.
- `./errors-goal-unreached-contract.md` — one stable error vocabulary serving operator, agent, and funnel; nothing may be reported as an empty result.
- `./siteconfig-singleton-row-store.md` — pk=1 forced save + get_or_create load; blank-means-unset; jurisdiction derived from country_code, never a stored toggle.
- `./dealstate-terminal-funnel.md` — six terminal-by-design states; not_before gates one row; job handle + attempt live on the deal; no deadline revert (double-charge regression).
- `./set-profile-state-log-vocabulary.md` — one write-helper owning state+log spelling; changed-vs-unchanged INFO/DEBUG split; NO EMAIL muted vs FAILED red.
- `./warm-start-label-rule.md` — labels from (state, outcome): non-FAILED ⇒ 1, FAILED+wrong_fit ⇒ 0, unknown skipped; enrichment miss stays a fit positive.
- `./create-lead-first-touch-ingest.md` — get_or_create on provider URL returns created; provenance first-touch only; query_terms enter embedding, never profile_text.
- `./mem0-factlist-summary-boundary.md` — vendored prompt instead of mem0ai's ~12 MB deps; seller-name identity binding; lazy derived cache; ADD/UPDATE/DELETE/NONE with logged skips.
- `./status-as-data-document.md` — one read-only dict, human/JSON projections; unknown ≠ zero credits; next-action arithmetic never asks before value exists.
- `./geo-two-regime-lines.md` — email-opt-in vs data-collection are two named country sets; both fail closed on missing codes; only the collection line strips whitespace.
- `./llm-persistent-loop-runner.md` — one daemon-thread asyncio loop as the sole sync→LLM boundary; run_sync portal poisoning + SDK `__del__` closed-loop GC bug are the rationale.
- `./llm-provider-ladder-verify-taxonomy.md` — bare model names route only via unambiguous prefixes else raise; verify catches ONLY provider-shaped errors as answers; bugs propagate.
- `./onboarding-env-hydration-ladder.md` — steps own done-check/run/env-path; all-or-nothing per step; absent means ask, set-but-bad means stop; consent never inferred.
- `./cli-output-contract.md` — stdout result-only; logs/banner/color/errors all stderr even under --json; only expected errors flatten to one typed line, exit 1; schema guard before work.
- `./find-goal-wiring-spend-optin.md` — count+noun budget grammar; unit implies flag in ONE direction; spending announced minute-zero; exit 0 ⇒ goal met; rows print before failing.

## Capsule map
- **Cycle & job kernel** — `cycle-priority-rows`: ROWS tuple of (name, step, spends); first True wins; may_spend gate skips only the paid row. `job-goal-bounded-run`: baseline-set subtraction collects goal entries once; `_presented_ids − baseline` caps new submissions; every exit is a JobResult, none raises; no timeout by design.
- **Paid enrichment leg** — `lookup-two-step-waterfall`: known-email → hub-cache → paid-submit ladder; couldn't-submit backs off instead of hot-looping; reclaim rescues handle-less FINDING_EMAIL deals. `bettercontact-async-split`: transport split per caller; Retry(status_forcelist=(429,), respect_retry_after_header=True); 401/402/RetryError → BetterContactUnavailable(error_type). `hub-give-to-get-store`: two best-effort calls degrade to no-ops; register_operator mints identity without contribution; build-sha rides every record.
- **Discovery walk** — `discovery-empty-semantics`: leads_found only meaningful at offset 0; spaced 5s retry before believing a zero; refusal re-raised, outage returns None. `select-frontier-beta-smoothing`: P̂=(a+2·P̂parent)/(a+b+2), θ~Beta(α,β); counts beat GP (0.661 vs 0.450 pearson). `select-retirement-prune`: offset-0 empty→dead+prune subtree; drained prunes; capped keeps subtree (fresh window). `labelstore-anchor-positives`: store = labelled profiles' token sets + anchors as positives; cooccurring() requires ≥1 qualified co-occurrence. `vocabulary-counted-growth`: refresh() recounts every pass (no cadence knob); df≥2 drops 65% junk tail. `icp-seed-vocabulary`: ICPSpec.domain_keywords ride lead_job_title (the only axis matching headline text); generate_anchors fills to ANCHOR_COUNT=3 and persists.
- **Qualification ML** — `qualifier-gp-bald`: Pipeline(StandardScaler→GPR RBF √d, alpha=0.1); anchors enter _training_arrays as permanent label-1 rows; balancing skipped while cold. `qualifier-acquisition-phases`: acquisition_mode returns exploit during cold regardless of balance (n_neg>n_pos is false by construction); qualifier_for() rebuilds per pass so labels are never stale. `ready-pool-spend-gate`: promote only QUALIFIED ≥ threshold; threshold read from CAMPAIGN_CONFIG, never passed; cycle._pool_signature memoizes (awaiting, past-gate) so idle campaigns don't refit GPs.
- **Output contract** — `export-importer-contract`: RECORD_FIELDS uses Instantly/Smartlead's exact names; exclude FAILED *and* Lead.disqualified (filtering only disqualified exported 1,944 rejections on the live install). `errors-goal-unreached-contract`: ErrorType strings are add-only CLI contract; GOAL_UNREACHED carries produced-of-goal plus pipeline_summary naming which gate holds.
- **State & status kernel (pass 2)** — `siteconfig-singleton-row-store`: save forces pk=1 so any instance IS the singleton; load get_or_create(pk=1); 18-caller write funnel. `dealstate-terminal-funnel`: state-is-the-queue — not_before, lookup_request_id, lookup_attempt all on the row; FINDING_EMAIL never re-deadlined (the old revert bought a second job for the same lead). `set-profile-state-log-vocabulary`: _STATE_LOG_STYLE table with visible ERROR fallback; unmapped state = red label, not silence; campaign-scoped FAILED+WRONG_FIT ≠ account-level Lead.disqualified. `warm-start-label-rule`: get_labeled_arrays maps deals→GP labels; NO_EMAIL_BETTERCONTACT is reachability-failed, fit-intact. `create-lead-first-touch-ingest`: discovered_by stamped once; query_terms vector-only split keeps the LLM judging firmographics alone. `mem0-factlist-summary-boundary`: reconcile mirrors mem0 c239d8a4 :594-700 with dict-for-vector-store substitution; hallucinated ids logged-skip. `status-as-data-document`: credits {"balance": None, "error": ErrorType} — unknown is its own answer; render_next_action lives in status.py so find's run end renders, never recomputes.
- **Operator & configuration plane (pass 3)** — `geo-two-regime-lines`: GDPR_COUNTRY_CODES (email opt-in, +ca/br/au/jp/kr/nz) vs EEA_UK_CH (collection regime) are deliberately disjoint; both default protected on missing codes; only the collection line strips whitespace ("a false drop costs one lead, a false keep is the only risk"). `llm-persistent-loop-runner`: one lazily-built daemon-thread loop via run_coroutine_threadsafe().result(); exists because Agent.run_sync poisons the caller's loop slot and per-call asyncio.run lets SDK client __del__ close transports on a dead loop; _MAX_RETRIES=8 rides SDK jitter + Retry-After. `llm-provider-ladder-verify-taxonomy`: split_model_id bare names route only via gpt/o1/o3/claude/gemini prefixes else raise; unknown provider raises listing all; verify_llm_credentials converts ONLY ModelAPIError/UserError/ValueError into answers — the anthropic-1.0.0 temperature TypeError must propagate; SILENCED_LOGGERS coupling test forces new providers to register everywhere. `onboarding-env-hydration-ladder`: Step(key, is_done, run, from_env, env_keys); hydrate in STEPS order, all-or-nothing per step; absent=ask vs set-but-bad=OnboardingEnvError naming the variable; ACCEPT_LEGAL_NOTICE never inferred; env newsletter defaults off everywhere; ensure_onboarded ladder ends in a typed error naming variables. `cli-output-contract`: stdout result-only; errors go to stderr even under --json ("find --json > leads.json"); only OpenOutreachError flattens to one typed line exit 1, bugs keep tracebacks; require_initialized_database fires after arg parsing (--help still answers), migrating verb opts out; termcolor's cached stdout-TTY answer pinned to stderr before first colored() call. `find-goal-wiring-spend-optin`: buy_addresses = flag OR unit==emails (the ONE implication direction; 2026-08-21 inversion — a forgotten flag costs a feature, never money); spending posture announced minute-zero; stdout carries WHOLE campaign so `> leads.csv` supersedes, --new narrows to produced_ids; rows print before GOAL_UNREACHED; exit 0 means goal met and nothing else; bare invocation prints OVERVIEW before Django imports.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenOutreach (GPL-3.0), `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory project `openoutreach` (FULL mode, 1,602 nodes / 6,909 edges, head==base==pin; parse_partial ×4 = jinja prompt templates + pytest.ini, none cited; core/vendor mem0 vendored dir BY DESIGN not-indexed). Pass-1 mined under project name `ext-openoutreach`, which no longer exists in the MCP registry (name instability precedent); pass-2 re-indexed the same checkout FULL under `openoutreach` — same HEAD, edge delta 6,971→6,909 is indexer-version drift on a rebuilt graph. Pass-3 revalidated live at the same pin (ready, identical counts) and mined the operator/configuration plane. Upstream has 2 newer commits afd4dff+38b2f58 touching status/hub balance display only — mined at pin; diff-first re-entry queued.

## Full view (memory graph)
Revalidate `openoutreach` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: priority-as-data hierarchy, set-delta goal accounting, parent-pointed Beta smoothing, retirement semantics keyed on offset, anchor-positive cold start, spend-gate singleness-of-purpose, importer-named export columns, stable error vocabulary, fail-closed jurisdiction defaults, absent-ask/set-but-bad-stop config vocabulary, stdout-result-only CLI contract. Adapt Django model plumbing (Deal/Lead/Campaign rows, SiteConfig), pydantic_ai Agent wiring, and the BetterContact/Lead Finder endpoint shapes to your provider. Omit the product surfaces this repo itself deleted (sending leg, mailboxes, warmth measurement, freemium promo campaign — all ported away to OpenEmailSequence or removed), the vendored mem0 tree under `openoutreach/core/vendor/`, the interactive questionary wizard internals, and Django-specific command registration/migration plumbing — while adopting the contracts that live above it: the output document (`status-as-data-document`), the base-command failure/guard shape and stderr logging plane (`cli-output-contract`), the env hydration ladder (`onboarding-env-hydration-ladder`), and find's goal/spend wiring (`find-goal-wiring-spend-optin`).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`bettercontact-async-split.md`](./bettercontact-async-split.md)
- [`cli-output-contract.md`](./cli-output-contract.md)
- [`create-lead-first-touch-ingest.md`](./create-lead-first-touch-ingest.md)
- [`cycle-priority-rows.md`](./cycle-priority-rows.md)
- [`dealstate-terminal-funnel.md`](./dealstate-terminal-funnel.md)
- [`discovery-empty-semantics.md`](./discovery-empty-semantics.md)
- [`errors-goal-unreached-contract.md`](./errors-goal-unreached-contract.md)
- [`export-importer-contract.md`](./export-importer-contract.md)
- [`find-goal-wiring-spend-optin.md`](./find-goal-wiring-spend-optin.md)
- [`geo-two-regime-lines.md`](./geo-two-regime-lines.md)
- [`hub-give-to-get-store.md`](./hub-give-to-get-store.md)
- [`icp-seed-vocabulary.md`](./icp-seed-vocabulary.md)
- [`job-goal-bounded-run.md`](./job-goal-bounded-run.md)
- [`labelstore-anchor-positives.md`](./labelstore-anchor-positives.md)
- [`llm-persistent-loop-runner.md`](./llm-persistent-loop-runner.md)
- [`llm-provider-ladder-verify-taxonomy.md`](./llm-provider-ladder-verify-taxonomy.md)
- [`lookup-two-step-waterfall.md`](./lookup-two-step-waterfall.md)
- [`mem0-factlist-summary-boundary.md`](./mem0-factlist-summary-boundary.md)
- [`onboarding-env-hydration-ladder.md`](./onboarding-env-hydration-ladder.md)
- [`qualifier-acquisition-phases.md`](./qualifier-acquisition-phases.md)
- [`qualifier-gp-bald.md`](./qualifier-gp-bald.md)
- [`ready-pool-spend-gate.md`](./ready-pool-spend-gate.md)
- [`select-frontier-beta-smoothing.md`](./select-frontier-beta-smoothing.md)
- [`select-retirement-prune.md`](./select-retirement-prune.md)
- [`set-profile-state-log-vocabulary.md`](./set-profile-state-log-vocabulary.md)
- [`siteconfig-singleton-row-store.md`](./siteconfig-singleton-row-store.md)
- [`status-as-data-document.md`](./status-as-data-document.md)
- [`vocabulary-counted-growth.md`](./vocabulary-counted-growth.md)
- [`warm-start-label-rule.md`](./warm-start-label-rule.md)
