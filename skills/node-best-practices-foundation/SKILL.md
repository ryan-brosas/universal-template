---
name: node-best-practices-foundation
description: "Use when porting Node.js production practice contracts: error-handling and crash predicates, project structure, testing patterns, Docker/ops choreography, and the security plane (headers, sessions, password KDFs, JWT revocation, injection/ReDoS guards, brute-force limiters, secret hygiene, sandbox ladders, OWASP checklist)."
disable-model-invocation: true
---
# Node.js Best Practices Foundation

## Use this for
Building or reviewing Node.js services against the community's distilled production contracts: operational-vs-programmer error taxonomy with crash predicates, promise-failure funnels, centralized handlers; component-first structure with 3-tier layering; AAA/named/five-outcome test contracts with ephemeral ports and black-box isolation; event-loop-preserving concurrency; Docker bootstrap, graceful shutdown, memory limits, multi-stage builds; uptime ownership and transaction correlation. Pass 2 adds the complete security plane: response-header matrix, session-cookie hardening, the bcrypt/scrypt/PBKDF2 selection ladder, timing-safe compare + CSPRNG, JWT revocation blacklists, safe redirects, shell-injection checklists, ReDoS guards, schema-validation gates, context-aware output escaping, ORM/parameterization rules, two-tier brute-force limiters, request throttling + payload caps, dependency audit pipelines, untrusted-code isolation ladders, eval-family bans, static require discipline, non-root execution, TLS termination, secrets/npm-publish hygiene, and the OWASP cross-cutting checklist. Pass 3 completes the remaining planes: Docker build-cache ordering/image hygiene/context-lint-scan gates, the stateless phoenix contract, reverse-proxy offload, NODE_ENV placement, maintenance-endpoint gates, dependency lock→npm-ci chain, monitoring/APM segmentation, fail-fast validation + three-layer error-flow tests, mature-logger and API-error-doc contracts, per-test data ownership + middleware isolation, native-over-userland lint gates, static-analysis ladders, framework selection, TypeScript dosage, hierarchical config, and the production-habits rubric. Source docs are CC-BY-SA-4.0 ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
### Error handling & quality (pass 1)
- `references/operational-vs-programmer-split.md` — the two-kind error taxonomy and the isTrustedError→process.exit(1) crash predicate.
- `references/unhandled-rejection-funnel.md` — why promise errors bypass uncaughtException and how the funnel catches them.
- `references/apperror-single-subclass.md` — one AppError class; setPrototypeOf(this, new.target.prototype) is load-bearing.
- `references/centralized-handler-not-middleware.md` — forward-only middleware plus a singleton handler for cron/queue/HTTP.
- `references/return-await-stacktrace-rule.md` — return await keeps the calling frame in the stack.
### Structure & testing (pass 1)
- `references/components-and-3-tiers.md` — components-first structure; transport types never enter the domain.
- `references/aaa-test-structure.md` — Arrange/Act/Assert with single-line act+assert discipline.
- `references/three-part-test-names.md` — unit/circumstance/expected naming grammar.
- `references/five-outcomes-test-coverage.md` — every test asserts response/state/external-call/queue/observability.
- `references/ephemeral-port-test-bootstrap.md` — PORT-env-or-0 boot for parallel CI.
- `references/nock-black-box-isolation.md` — intercept + fail-closed disableNetConnect + payload assertions.
### Runtime & ops (pass 1)
- `references/event-loop-non-blocking.md` — small per-client work; offload CPU-bound paths.
- `references/node-direct-bootstrap.md` — exec-form CMD node / TINI as PID1 so signals arrive.
- `references/graceful-shutdown-choreography.md` — drain→stop-new→cleanup→log inside the SIGTERM budget.
- `references/dual-memory-limits.md` — Docker placement limit paired with v8 --max-old-space-size.
- `references/multi-stage-build-and-secrets.md` — prod-only install; build-arg secrets persist in image history.
- `references/uptime-ownership-ladder.md` — the layer holding placement data owns restarts.
- `references/transaction-id-correlation.md` — AsyncLocalStorage + x-transaction-id header correlation.
### Security plane (pass 2)
- `references/security-header-matrix.md` — eight headers with parameter-level semantics (HSTS/CSP/XFO/XCTO/…).
- `references/session-cookie-hardening.md` — rename connect.sid, secure/httpOnly/maxAge off default.
- `references/password-kdf-ladder.md` — bcrypt cost12 / scrypt N32768 / PBKDF2 floors; bcrypt's 64-byte trap; Math.random ban.
- `references/commonsecurity-random-compare.md` — timingSafeEqual for hashes; crypto.randomBytes for tokens; lint detectors.
- `references/jwt-revocation-blacklist.md` — jti-keyed blacklist on an EXTERNAL store; statelessness deliberately sacrificed.
- `references/safe-redirect-whitelist.md` — `^\/(?!\/)` relative-path guard + whitelist + '/' fallback kills open redirects.
- `references/childprocess-shell-injection.md` — exec(string+input) = RCE; avoid>sanitize>least-privilege>isolate checklist.
- `references/redos-safe-regex-guard.md` — nested-repetition bombs freeze the loop; safe-regex gate + validator substitution.
- `references/schema-validation-gate.md` — declare accept-set, enforce via middleware before handlers, 400 on deviation.
- `references/context-aware-output-escaping.md` — five never-sinks; escape per output context, entity-encoding alone fails.
- `references/error-detail-suppression.md` — production error handler renders message + empty error object; stacks never reach clients.
- `references/injection-proof-data-access.md` — validate + ORM parameterization; the NoSQL $where JS-injection trap.
- `references/two-tier-brute-force-limiter.md` — username+IP consecutive limiter × IP-per-day total limiter, both shared-store.
- `references/request-throttling-and-payload-caps.md` — points/duration/block per client + body-size caps at app or proxy edge.
- `references/dependency-audit-pipeline.md` — npm audit baseline + auto-fix PR services; recurring not one-shot.
- `references/untrusted-code-sandbox-ladder.md` — child process > serverless > vm-library; containment semantics to verify.
- `references/eval-family-ban.md` — eval/setTimeout-string/setInterval-string/new Function are one hole; lint-enforced ban.
- `references/static-require-discipline.md` — literal require/fs specifiers when input-derived; the four detector rules.
- `references/non-root-execution-contract.md` — USER node placement + unprivileged ports + proxy for <1024.
- `references/tls-termination-shape.md` — https.createServer cert pair or proxy-side SSL; pick per topology.
- `references/secrets-env-and-npm-publish.md` — env-vars litmus, cryptr exception, .npmignore-overrides-.gitignore trap.
- `references/owasp-control-checklist.md` — A2/A3/A5/A6/A7/A9/A10 families + PII + security.txt reporting surfaces.
### Docker deep plane (pass 3)
- `references/docker-build-cache-ordering.md` — stable→volatile layer ladder; one invalidated layer poisons all later layers; deps-before-source.
- `references/docker-image-slimming-tagging.md` — --force cache clean, slim/alpine ladder, the :latest default-tag matrix.
- `references/docker-context-lint-scan-gate.md` — .dockerignore secrets → hadolint structure lint → final-image CVE scan, in that order.
### Production & ops plane (pass 3)
- `references/stateless-phoenix-contract.md` — multer uploads / file-session stores / global caches are the three kill-and-replace breakers.
- `references/reverse-proxy-offload-ladder.md` — static/gzip/TLS/throttle leave the Node process; proxy or cloud storage/CDN serve them.
- `references/node-env-production-contract.md` — deploy-time env var; unset ⇒ ~3x throughput loss on Express-class stacks.
- `references/maintenance-endpoint-gates.md` — external-tools-first golden rule; admin-gated, DDoS-target-aware ops routes only.
- `references/dependency-lock-exact-chain.md` — save-exact → committed lockfile → npm ci (fail-on-mismatch) → LTS runtime.
- `references/monitoring-apm-segmentation.md` — six core metrics, hardware-vs-in-process blind spots, APM as the UX-level tier.
- `references/production-code-habits-checklist.md` — named functions for profiles, trace-sync-io CI detection, test-like-production, JSON+transaction-id logs.
### Error-handling & performance long tail (pass 3)
- `references/failfast-and-error-flow-tests.md` — Joi.assert-first entry validation + three-layer error-flow tests incl. logged-fields contract.
- `references/mature-logger-contract.md` — four logger requirements + timestamp/machine-readable floor; console.log disqualified.
- `references/api-error-doc-contract.md` — errors documented as schema (OpenAPI statuses / GraphQL error shape), not release notes.
- `references/native-over-userland-lint-gate.md` — conditional native-first rule (~50% aggregate gain) enforced by the YDNLU ESLint plugin.
### Structure & quality stragglers (pass 3)
- `references/static-analysis-quality-ladder.md` — Prettier formats, ESLint lints single files, Sonar-class blocks builds on cross-file smells.
- `references/hierarchical-config-contract.md` — files+hierarchy+env-overrides+secret-exclusion+boot-time validation (convict-class).
- `references/per-test-data-and-middleware-isolation.md` — each test owns its rows (seed = hidden coupling); middleware tested via {req,res} doubles.
- `references/framework-selection-matrix.md` — popularity-weighted pros/cons + four "prefer X when" rules keyed to team skill and app shape.
- `references/typescript-dosage-rule.md` — type-safety vs design-constructs are distinct offers; adopt types deliberately, skip OOP drift.
### Coverage-closure stragglers (pass 5)
- `references/four-signals-service-watchlist.md` — Error Rate / Response time / Throughput / Saturation watchlist for EVERY service; alerting-first definition of monitoring; per-service complement to the six-metric ops floor.
- `references/utility-wrap-private-package.md` — wrap 3rd-party utilities behind your own module and publish as a PRIVATE npm package (private modules / registry / local); one copy, N consumer components, replaceability lives at the facade.

## Capsule map
- **Error handling** — `operational-vs-programmer-split`, `unhandled-rejection-funnel`, `apperror-single-subclass`, `centralized-handler-not-middleware`, `return-await-stacktrace-rule`: classify errors by operator-fixability, crash fast on programmer bugs while funneling async failures to one handler that keeps stack frames and never loses the original cause.
- **Structure & testing** — `components-and-3-tiers`, `aaa-test-structure`, `three-part-test-names`, `five-outcomes-test-coverage`, `ephemeral-port-test-bootstrap`, `nock-black-box-isolation`: components-first layout with strict layer boundaries, tests named by unit/circumstance/expected covering all five outcome kinds, random-port boots for parallel CI, and fail-closed network isolation.
- **Runtime & ops** — `event-loop-non-blocking`, `node-direct-bootstrap`, `graceful-shutdown-choreography`, `dual-memory-limits`, `multi-stage-build-and-secrets`, `uptime-ownership-ladder`, `transaction-id-correlation`: keep the loop responsive, be PID1 to receive SIGTERM, drain in the grace budget, cap memory at placement AND GC layers, keep build-time secrets out of final images, and let the orchestrator-aware layer own restarts.
- **Web surface security** — `security-header-matrix`, `session-cookie-hardening`, `safe-redirect-whitelist`, `context-aware-output-escaping`, `schema-validation-gate`, `error-detail-suppression`: header matrix + renamed/secured cookies + redirect whitelisting + per-context escaping + early schema gates + status-code-only production errors form one defense chain over HTTP traffic.
- **Crypto & identity** — `password-kdf-ladder`, `commonsecurity-random-compare`, `jwt-revocation-blacklist`, `tls-termination-shape`: KDF selection with pinned floors and salt discipline, constant-time compares with CSPRNG token generation, externally-stored JWT revocation, TLS terminated at Node or the proxy.
- **Injection & execution safety** — `childprocess-shell-injection`, `redos-safe-regex-guard`, `injection-proof-data-access`, `eval-family-ban`, `static-require-discipline`, `untrusted-code-sandbox-ladder`: every string-to-execution sink (shell, regex engine, SQL/NoSQL parser, eval family, module resolver) gets an explicit guard, with the isolation ladder for genuinely untrusted code.
- **Traffic & dependency hardening** — `two-tier-brute-force-limiter`, `request-throttling-and-payload-caps`, `dependency-audit-pipeline`: identity-pair × IP-total rate limiting distinct from throughput throttling and payload caps, with recurring dependency audits closing the supply-chain loop.
- **Hygiene & governance** — `secrets-env-and-npm-publish`, `non-root-execution-contract`, `owasp-control-checklist`: env-var litmus + publish-path traps, least-privilege container runtime, and the periodic OWASP-family audit template.
- **Docker deep plane** — `docker-build-cache-ordering`, `docker-image-slimming-tagging`, `docker-context-lint-scan-gate`: cache-preserving instruction order, image shrink + tag discipline, and the context→lint→scan gate sequence that keeps secrets out and CVEs visible before an image ships.
- **Production & ops** — `stateless-phoenix-contract`, `reverse-proxy-offload-ladder`, `node-env-production-contract`, `maintenance-endpoint-gates`, `dependency-lock-exact-chain`, `monitoring-apm-segmentation`, `four-signals-service-watchlist`, `production-code-habits-checklist`: no local-only state, networking tasks offloaded to proxies, NODE_ENV set at deploy time, ops endpoints gated and scoped, the lock→npm-ci reproducibility chain, the two-plane monitoring floor plus the per-service four-signal watchlist, and the pre-ship habits rubric.
- **Ops long tail** — `failfast-and-error-flow-tests`, `mature-logger-contract`, `api-error-doc-contract`, `native-over-userland-lint-gate`, `static-analysis-quality-ladder`: entry validation with tested failure paths, leveled JSON logging, error-as-schema documentation, and lint/build gates covering natives-vs-userland plus cross-file smells.
- **Structure decisions** — `hierarchical-config-contract`, `per-test-data-and-middleware-isolation`, `framework-selection-matrix`, `typescript-dosage-rule`, `utility-wrap-private-package`: boot-validated layered config, per-test data ownership with serverless middleware tests, signal-driven framework choice, deliberate TypeScript dosage, and one-copy shared-utility distribution behind private npm facades.

## Extending the foundation
Add one `references/<practice>.md` capsule-v2 for one practice doc whose contract a porter could get wrong; cite the section path + line anchors, pin a deterministic grep probe (no upstream runner exists), and add the matching loader line + map entry.

## Provenance
nodebestpractices (Goldbergs et al.), CC-BY-SA-4.0, `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory project `nodebestpractices`. Pass 1 ([DONE:136], 2026-08-23): 18 capsules over errorhandling/projectstructre/testingandquality/docker/production planes; 18 cited paths `no_recorded_issue`. Pass 2 (2026-08-23, docs-knowledge lane; capsule files landed in commit `99234b6` by a sibling run that died before records — adopted, source-verified at pin, and all 40 probes repaired to verbatim-executable form by the rescue entry [DONE:205]): security plane completed whole-file — all 24 English docs in `sections/security/` read top-to-bottom into 22 new capsule-v2 (one merge of overlapping sessions/headers content). Pass 3 (2026-08-24, docs-knowledge cron lane `drain-lane-docs-knowledge`): citation-vs-inventory sweep at stem level exposed 44 never-cited English docs → remaining planes completed whole-file into 19 new capsule-v2 (40→59) + production-twin cross-link added to `dependency-audit-pipeline`; upstream HEAD unchanged `dc3d60c` (fetched, behind=0); graph re-verified live at identical counts. Pass 4 (2026-08-24, docs-knowledge verification lane): FIRST full byte-exact battery across all 59 capsules — 105 probe commands executed (85 green as-shipped; 20 extractor artifacts adjudicated: expected-output spans/placeholders, not capsule defects) and all 78 search_graph Retrieves found DEAD (doc-shaped-graph BM25 class — the leaf's own Full-view caveat, never applied per-capsule) → every dead block rewritten to executed search_code form with a needle derived from that capsule's own Probe anchors and live-verified to resolve its pinned file line-exact (38/38 search_code entries already live). Post-repair battery: 192/192 retrieves LIVE. Pass 5 (2026-08-25, FAC-80 lane miner-nodebestpractices): stem-level closure sweep against the graph's exact English inventory (92 docs) exposed ONE never-cited doc (`errorhandling/monitoring.md`) plus one partial (`wraputilities.md` — single invariant clause inside `components-and-3-tiers`) → mined both whole-file into 2 new capsule-v2 (59→61 refs), added the production-twin cross-link to `monitoring-apm-segmentation`, repointed the components-and-3-tiers utilities clause to the new capsule; all 8 probes executed green at pin; both Retrieves live via `search_code` (single-result exact-file resolutions); remaining uncited set = excluded-with-reason only (drafts ×4, thincomponents, bumpversion stub) ⇒ English corpus CLOSED at stem level until upstream HEAD advances past dc3d60c.

## Full view (memory graph)
Revalidate `nodebestpractices` before porting: run `index_status`, `check_index_coverage`, `search_code`, `get_architecture`. Live at last verification (2026-08-24): root `/mnt/hdd/utopia/inspo/frameworks/nodebestpractices` (canonical worktree; project root_path records `/mnt/hdd/utopia/inspo/nodebestpractices`), branch master@dc3d60c (HEAD==base), FULL mode, 6,007 nodes / 6,013 edges, zero parse_partial, 80 image assets excluded-by-design. Doc-shaped graph: 4,632 Section / 661 File / 661 Module nodes; NOTE — BM25 `search_graph` text queries return ZERO on this graph (only 3 shell-script Function nodes carry searchable tokens); use `search_code --pattern <stem>` for retrieval and `check_index_coverage` for freshness. The README is the TL;DR index; section docs carry the deep code examples cited here. Source docs decide shipped claims; no upstream test runner exists (probes are deterministic greps).

## Boundaries
Adopt the practice contracts and their invariants (crash predicate, drain order, KDF floors, external revocation store, two-tier limiter shape, layer-order/cache-bust rules, stateless trio ban, lock→npm-ci chain); adapt library choices (Helmet/joi/rate-limiter-flexible equivalents), thresholds, and tool names to your stack; omit version-pinned specifics that upstream has since superseded (X-XSS-Protection auditor removal, HPKP→Expect-CT deprecation, doc-era size/throughput figures — noted in-capsule), translation READMEs, drafts/, assets/, `.operations/` governance corpus (community authoring workflow — repo-meta only, no Node contract), template.md scaffold, bumpversion.md stub (placeholder "Title here"), thincomponents.md (component doctrine already carried by components-and-3-tiers from pass 1), and generic-tips' language-agnostic items beyond their Node-relevant guards. Coverage caveat: probes are deterministic line-anchored greps against a docs-only repo — no behavioral runner exists upstream.
