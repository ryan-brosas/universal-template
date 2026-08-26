---
name: railway-nexus3-foundation
description: "Railway deployment template foundation: first-boot credential rotation, anonymous-access hardening, EULA consent gating in automation, slow-boot healthcheck budgets, signal relay, and static template tests."
disable-model-invocation: true
---

# railway-template-nexus3: Railway deployment template foundation

## Use this for
Use when building a one-click platform (Railway/Render/Fly/compose) template for a stateful service with first-boot credential generation — bootstrap-once password rotation, anonymous-access hardening, EULA consent gating in automation, slow-boot healthcheck budgets, dual-path signal handling, and static template tests. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/bootstrap-once-gate.md` — how the entrypoint rotates the generated admin password exactly once across restarts via a volume marker.
- `references/least-privilege-drop.md` — root-prep → su-exec UID 200 split so the JVM never runs as root.
- `references/anonymous-disable.md` — the full-body PUT that disables Nexus's anonymous realm and why it fires after rotation.
- `references/eula-consent-gate.md` — read→check→refuse-unless-opt-in→echo-disclaimer ladder so automation never accepts legal terms by default.
- `references/smoke-crud-roundtrip.md` — five-assertion live verification ending in a byte-exact write/read-back through a fresh repo.
- `references/platform-healthcheck-contract.md` — matched 900 s budgets between platform probe and in-container bootstrap loop; ON_FAILURE ×10; single-replica sizing.
- `references/static-template-tests.md` — six regex pins in plain node that keep the security-critical literals from rotting.
- `references/env-gate-fail-closed.md` — fail-closed environment variable validation before service initialization.
- `references/initial-credential-single-use.md` — single-use initial credential consumption and secure purging protocol.
- `references/readiness-conjunction-poll.md` — multi-port readiness conjunction polling during container startup.
- `references/signal-relay-dual-path.md` — dual-path signal relay for graceful shutdown propagation between host and guest.
- `references/errexit-fail-fast-budget.md` — `set -eu` as the failure budget for every bootstrap step; probes-under-`if` exemption and its mutation-side trap.
- `references/loopback-only-mutation-surface.md` — all credential-bearing API mutations target 127.0.0.1; public surface limited to health + authenticated reads.
- `references/version-pinned-supply-chain.md` — digest-pinned base image plus the same version restated across README/TEMPLATE_README/THIRD_PARTY_NOTICES as one four-carrier fact.
- `references/docs-as-deployed-contract.md` — doc claims (rotation, anonymous-off, idempotency marker, sizing) are contract statements mirroring entrypoint invariants.
- `references/npm-test-template-gate.md` — zero-dependency `"type":"module"` npm-test gate so file-text assertions run anywhere bare node runs.
- `references/verifier-request-hygiene.md` — post-deploy verifier request hygiene: normalize-once `BASE_URL.rstrip('/')`, mandatory explicit timeouts classed 60 s (warmup/storage ops) vs 30 s (reads), success marker naming the probe repo.
- `references/template-readme-sections.md` — the fixed six-section marketplace README skeleton (title-as-task, About Hosting, Common Use Cases, Dependencies+subsections, Implementation Details, Why Deploy) and which claim class belongs in each.

## Capsule map
- **Bootstrap-once rotation** — `bootstrap-once-gate`, `initial-credential-single-use`: marker-gated split entrypoint; rotate generated→operator password strictly before marker touch; single-use credential purging.
- **Least-privilege container** — `least-privilege-drop`, `signal-relay-dual-path`: USER-root only for mkdir/chown of `/nexus-data`; su-exec execution; dual-path signal forwarding.
- **Anonymous-off bootstrap step** — `anonymous-disable`: full-state-toggle JSON body (`enabled:false, userId, realmName`) with fail-loud curl under `set -eu`.
- **EULA consent gate** — `eula-consent-gate`, `env-gate-fail-closed`: default-deny consent; `.get('accepted', False)` fails toward refusal; fail-closed environment gating.
- **Live CRUD smoke** — `smoke-crud-roundtrip`, `verifier-request-hygiene`: health → anon-blocked → wrong-auth rejected → good-auth accepted → unique-named repo + byte-exact round-trip; verifier request hygiene (normalize-once base URL, 60 s warmup/storage vs 30 s read timeout classes, repo-naming success marker).
- **Slow-boot liveness pair** — `platform-healthcheck-contract`, `readiness-conjunction-poll`: platform timeout == internal poll budget (900 s); conjunction readiness polling.
- **Static template tests** — `static-template-tests`, `npm-test-template-gate`: assert load-bearing literals (digest pin, no :latest, change-password, enabled:false, status path, EULA env) with zero services; the zero-dependency npm-test wiring that runs them anywhere.
- **Fail-fast & network surface** — `errexit-fail-fast-budget`, `loopback-only-mutation-surface`: errexit budget over every mutation (probes-under-`if` exemption, mutation-side trap); loopback-only privileged traffic vs public health/read surface.
- **Supply-chain & docs contract** — `version-pinned-supply-chain`, `docs-as-deployed-contract`, `template-readme-sections`: digest+version four-carrier fact; doc claims as deployable contract mirroring entrypoint invariants; the marketplace README's fixed section skeleton with per-section claim classes.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
railway-template-nexus3 (EPL-1.0), `main@18e177a6563436ca1cd7e44bc2fa5648f6735c58` (3.95.2 digest bump over the pass-1 pin `95cd7b9a`; all capsule seams byte-verified unchanged); Codebase Memory project `railway-template-nexus3` (canonical root `/mnt/hdd/utopia/inspo/railway-template-nexus3`, branch main, head==base==pin, 73 nodes / 110 edges, full mode, generation 2026-08-25T08:42:38Z, zero parse_partial/skipped; config-shaped graph — shell/TOML flow confirmed by whole-file source reads). TWIN RESOLVED pass 6: the retired long-name project `mnt-hdd-utopia-inspo-reference-railway-template-nexus3` is gone from list_projects; the short-name project was refreshed IN PLACE at the canonical root and now serves the pin (an accidental derived-name duplicate created by that refresh was deleted immediately). Pass-5 deepening-B re-entry @ UNCHANGED pin: +5 capsule-v2 (11→16) mining the previously-unmined seams (`set -eu` budget incl. the if-context exemption trap, loopback-only mutation surface, four-carrier version pinning, docs-as-contract, npm-test gate); repaired stale `3\.95\.1` probe literals to `3\.95\.2` in `least-privilege-drop` + `static-template-tests` and restored curly quotes in `eula-consent-gate`'s disclaimer excerpt; `node tests/static.mjs` rc=0 and env-gate behavioral probe re-executed at pin. Pass-6 deep-learning re-mine @ UNCHANGED pin: +2 capsule-v2 (16→18) after whole-repo coverage audit adjudicated crash-loop economics, marker-chown symmetry, exit-code propagation, negative-set tolerance, and four-carrier census as ALREADY covered (non-gaps recorded in work record) — new seams are verifier request hygiene (normalize-once BASE_URL, 6×30 s vs 3×60 s timeout classes, repo-naming success marker) and the marketplace README six-section skeleton; fleet retrieval-parity repair replaced 20 dead citations of the retired graph-project name with the live short-name across 15 capsules + this file; `node tests/static.mjs` rc=0; work record CREATED at inspo/railway-template-nexus3-work/ (was absent passes 1–5).

Pass-7 quality-only closure pass (2026-08-26) @ UNCHANGED pin `18e177a65634…`: checkout HEAD/tree verified == pin, no upstream advance; Gate-1 re-run (73n/110e, zero parse-partial/skipped); the full eighteen-capsule Probe + Retrieve battery re-executed byte-for-byte with ZERO drift from recorded values (both recorded negative caveats reconfirmed live); parity re-verified 18 loader bullets == 18 disk refs; repo row migrated into the canonical `.skill-mining-work/llm-repo-learning.md` ledger; no reference file changed.

## Full view (memory graph)
Revalidate `railway-template-nexus3` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the template-engineering contracts (bootstrap-once gate, consent gating, matched liveness budgets, static literal pins, fail-fast errexit budget, loopback-only privileged surface); adapt paths, UIDs, ports, and REST endpoints per product; omit Railway-specific wiring and the upstream Nexus product behavior itself (covered by `nexus-public-foundation`).
