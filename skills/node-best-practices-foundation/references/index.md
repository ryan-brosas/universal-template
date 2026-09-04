<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Node.js Best Practices Foundation

## Use this for
Building or reviewing Node.js services against the community's distilled production contracts: operational-vs-programmer error taxonomy with crash predicates, promise-failure funnels, centralized handlers; component-first structure with 3-tier layering; AAA/named/five-outcome test contracts with ephemeral ports and black-box isolation; event-loop-preserving concurrency; Docker bootstrap, graceful shutdown, memory limits, multi-stage builds; uptime ownership and transaction correlation. Pass 2 adds the complete security plane: response-header matrix, session-cookie hardening, the bcrypt/scrypt/PBKDF2 selection ladder, timing-safe compare + CSPRNG, JWT revocation blacklists, safe redirects, shell-injection checklists, ReDoS guards, schema-validation gates, context-aware output escaping, ORM/parameterization rules, two-tier brute-force limiters, request throttling + payload caps, dependency audit pipelines, untrusted-code isolation ladders, eval-family bans, static require discipline, non-root execution, TLS termination, secrets/npm-publish hygiene, and the OWASP cross-cutting checklist. Pass 3 completes the remaining planes: Docker build-cache ordering/image hygiene/context-lint-scan gates, the stateless phoenix contract, reverse-proxy offload, NODE_ENV placement, maintenance-endpoint gates, dependency lock→npm-ci chain, monitoring/APM segmentation, fail-fast validation + three-layer error-flow tests, mature-logger and API-error-doc contracts, per-test data ownership + middleware isolation, native-over-userland lint gates, static-analysis ladders, framework selection, TypeScript dosage, hierarchical config, and the production-habits rubric. Source docs are CC-BY-SA-4.0 ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
### Error handling & quality (pass 1)
- `./operational-vs-programmer-split.md` — the two-kind error taxonomy and the isTrustedError→process.exit(1) crash predicate.
- `./unhandled-rejection-funnel.md` — why promise errors bypass uncaughtException and how the funnel catches them.
- `./apperror-single-subclass.md` — one AppError class; setPrototypeOf(this, new.target.prototype) is load-bearing.
- `./centralized-handler-not-middleware.md` — forward-only middleware plus a singleton handler for cron/queue/HTTP.
- `./return-await-stacktrace-rule.md` — return await keeps the calling frame in the stack.
### Structure & testing (pass 1)
- `./components-and-3-tiers.md` — components-first structure; transport types never enter the domain.
- `./aaa-test-structure.md` — Arrange/Act/Assert with single-line act+assert discipline.
- `./three-part-test-names.md` — unit/circumstance/expected naming grammar.
- `./five-outcomes-test-coverage.md` — every test asserts response/state/external-call/queue/observability.
- `./ephemeral-port-test-bootstrap.md` — PORT-env-or-0 boot for parallel CI.
- `./nock-black-box-isolation.md` — intercept + fail-closed disableNetConnect + payload assertions.
### Runtime & ops (pass 1)
- `./event-loop-non-blocking.md` — small per-client work; offload CPU-bound paths.
- `./node-direct-bootstrap.md` — exec-form CMD node / TINI as PID1 so signals arrive.
- `./graceful-shutdown-choreography.md` — drain→stop-new→cleanup→log inside the SIGTERM budget.
- `./dual-memory-limits.md` — Docker placement limit paired with v8 --max-old-space-size.
- `./multi-stage-build-and-secrets.md` — prod-only install; build-arg secrets persist in image history.
- `./uptime-ownership-ladder.md` — the layer holding placement data owns restarts.
- `./transaction-id-correlation.md` — AsyncLocalStorage + x-transaction-id header correlation.
### Security plane (pass 2)
- `./security-header-matrix.md` — eight headers with parameter-level semantics (HSTS/CSP/XFO/XCTO/…).
- `./session-cookie-hardening.md` — rename connect.sid, secure/httpOnly/maxAge off default.
- `./password-kdf-ladder.md` — bcrypt cost12 / scrypt N32768 / PBKDF2 floors; bcrypt's 64-byte trap; Math.random ban.
- `./commonsecurity-random-compare.md` — timingSafeEqual for hashes; crypto.randomBytes for tokens; lint detectors.
- `./jwt-revocation-blacklist.md` — jti-keyed blacklist on an EXTERNAL store; statelessness deliberately sacrificed.
- `./safe-redirect-whitelist.md` — `^\/(?!\/)` relative-path guard + whitelist + '/' fallback kills open redirects.
- `./childprocess-shell-injection.md` — exec(string+input) = RCE; avoid>sanitize>least-privilege>isolate checklist.
- `./redos-safe-regex-guard.md` — nested-repetition bombs freeze the loop; safe-regex gate + validator substitution.
- `./schema-validation-gate.md` — declare accept-set, enforce via middleware before handlers, 400 on deviation.
- `./context-aware-output-escaping.md` — five never-sinks; escape per output context, entity-encoding alone fails.
- `./error-detail-suppression.md` — production error handler renders message + empty error object; stacks never reach clients.
- `./injection-proof-data-access.md` — validate + ORM parameterization; the NoSQL $where JS-injection trap.
- `./two-tier-brute-force-limiter.md` — username+IP consecutive limiter × IP-per-day total limiter, both shared-store.
- `./request-throttling-and-payload-caps.md` — points/duration/block per client + body-size caps at app or proxy edge.
- `./dependency-audit-pipeline.md` — npm audit baseline + auto-fix PR services; recurring not one-shot.
- `./untrusted-code-sandbox-ladder.md` — child process > serverless > vm-library; containment semantics to verify.
- `./eval-family-ban.md` — eval/setTimeout-string/setInterval-string/new Function are one hole; lint-enforced ban.
- `./static-require-discipline.md` — literal require/fs specifiers when input-derived; the four detector rules.
- `./non-root-execution-contract.md` — USER node placement + unprivileged ports + proxy for <1024.
- `./tls-termination-shape.md` — https.createServer cert pair or proxy-side SSL; pick per topology.
- `./secrets-env-and-npm-publish.md` — env-vars litmus, cryptr exception, .npmignore-overrides-.gitignore trap.
- `./owasp-control-checklist.md` — A2/A3/A5/A6/A7/A9/A10 families + PII + security.txt reporting surfaces.
### Docker deep plane (pass 3)
- `./docker-build-cache-ordering.md` — stable→volatile layer ladder; one invalidated layer poisons all later layers; deps-before-source.
- `./docker-image-slimming-tagging.md` — --force cache clean, slim/alpine ladder, the :latest default-tag matrix.
- `./docker-context-lint-scan-gate.md` — .dockerignore secrets → hadolint structure lint → final-image CVE scan, in that order.
### Production & ops plane (pass 3)
- `./stateless-phoenix-contract.md` — multer uploads / file-session stores / global caches are the three kill-and-replace breakers.
- `./reverse-proxy-offload-ladder.md` — static/gzip/TLS/throttle leave the Node process; proxy or cloud storage/CDN serve them.
- `./node-env-production-contract.md` — deploy-time env var; unset ⇒ ~3x throughput loss on Express-class stacks.
- `./maintenance-endpoint-gates.md` — external-tools-first golden rule; admin-gated, DDoS-target-aware ops routes only.
- `./dependency-lock-exact-chain.md` — save-exact → committed lockfile → npm ci (fail-on-mismatch) → LTS runtime.
- `./monitoring-apm-segmentation.md` — six core metrics, hardware-vs-in-process blind spots, APM as the UX-level tier.
- `./production-code-habits-checklist.md` — named functions for profiles, trace-sync-io CI detection, test-like-production, JSON+transaction-id logs.
### Error-handling & performance long tail (pass 3)
- `./failfast-and-error-flow-tests.md` — Joi.assert-first entry validation + three-layer error-flow tests incl. logged-fields contract.
- `./mature-logger-contract.md` — four logger requirements + timestamp/machine-readable floor; console.log disqualified.
- `./log-routing-to-stdout.md` — app code writes unbuffered to stdout/stderr ONLY; log destinations (file/DB/SaaS) belong to the execution environment's log-driver, so changing them never requires a deploy.
- `./api-error-doc-contract.md` — errors documented as schema (OpenAPI statuses / GraphQL error shape), not release notes.
- `./native-over-userland-lint-gate.md` — conditional native-first rule (~50% aggregate gain) enforced by the YDNLU ESLint plugin.
### Structure & quality stragglers (pass 3)
- `./static-analysis-quality-ladder.md` — Prettier formats, ESLint lints single files, Sonar-class blocks builds on cross-file smells.
- `./hierarchical-config-contract.md` — files+hierarchy+env-overrides+secret-exclusion+boot-time validation (convict-class).
- `./per-test-data-and-middleware-isolation.md` — each test owns its rows (seed = hidden coupling); middleware tested via {req,res} doubles.
- `./framework-selection-matrix.md` — popularity-weighted pros/cons + four "prefer X when" rules keyed to team skill and app shape.
- `./typescript-dosage-rule.md` — type-safety vs design-constructs are distinct offers; adopt types deliberately, skip OOP drift.
### Coverage-closure stragglers (pass 5)
- `./four-signals-service-watchlist.md` — Error Rate / Response time / Throughput / Saturation watchlist for EVERY service; alerting-first definition of monitoring; per-service complement to the six-metric ops floor.
- `./utility-wrap-private-package.md` — wrap 3rd-party utilities behind your own module and publish as a PRIVATE npm package (private modules / registry / local); one copy, N consumer components, replaceability lives at the facade.

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
- **Ops long tail** — `failfast-and-error-flow-tests`, `mature-logger-contract`, `log-routing-to-stdout`, `api-error-doc-contract`, `native-over-userland-lint-gate`, `static-analysis-quality-ladder`: entry validation with tested failure paths, leveled JSON logging with stdout-only routing owned by the execution environment, error-as-schema documentation, and lint/build gates covering natives-vs-userland plus cross-file smells.
- **Structure decisions** — `hierarchical-config-contract`, `per-test-data-and-middleware-isolation`, `framework-selection-matrix`, `typescript-dosage-rule`, `utility-wrap-private-package`: boot-validated layered config, per-test data ownership with serverless middleware tests, signal-driven framework choice, deliberate TypeScript dosage, and one-copy shared-utility distribution behind private npm facades.

## Extending the foundation
Add one `./<practice>.md` capsule-v2 for one practice doc whose contract a porter could get wrong; cite the section path + line anchors, pin a deterministic grep probe (no upstream runner exists), and add the matching loader line + map entry.

## Provenance
nodebestpractices (Goldbergs et al.), CC-BY-SA-4.0, `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory project `nodebestpractices`. Pass 1 ([DONE:136], 2026-08-23): 18 capsules over errorhandling/projectstructre/testingandquality/docker/production planes; 18 cited paths `no_recorded_issue`. Pass 2 (2026-08-23, docs-knowledge lane; capsule files landed in commit `99234b6` by a sibling run that died before records — adopted, source-verified at pin, and all 40 probes repaired to verbatim-executable form by the rescue entry [DONE:205]): security plane completed whole-file — all 24 English docs in `sections/security/` read top-to-bottom into 22 new capsule-v2 (one merge of overlapping sessions/headers content). Pass 3 (2026-08-24, docs-knowledge cron lane `drain-lane-docs-knowledge`): citation-vs-inventory sweep at stem level exposed 44 never-cited English docs → remaining planes completed whole-file into 19 new capsule-v2 (40→59) + production-twin cross-link added to `dependency-audit-pipeline`; upstream HEAD unchanged `dc3d60c` (fetched, behind=0); graph re-verified live at identical counts. Pass 4 (2026-08-24, docs-knowledge verification lane): FIRST full byte-exact battery across all 59 capsules — 105 probe commands executed (85 green as-shipped; 20 extractor artifacts adjudicated: expected-output spans/placeholders, not capsule defects) and all 78 search_graph Retrieves found DEAD (doc-shaped-graph BM25 class — the leaf's own Full-view caveat, never applied per-capsule) → every dead block rewritten to executed search_code form with a needle derived from that capsule's own Probe anchors and live-verified to resolve its pinned file line-exact (38/38 search_code entries already live). Post-repair battery: 192/192 retrieves LIVE. Pass 5 (2026-08-25, FAC-80 lane miner-nodebestpractices): stem-level closure sweep against the graph's exact English inventory (92 docs) exposed ONE never-cited doc (`errorhandling/monitoring.md`) plus one partial (`wraputilities.md` — single invariant clause inside `components-and-3-tiers`) → mined both whole-file into 2 new capsule-v2 (59→61 refs), added the production-twin cross-link to `monitoring-apm-segmentation`, repointed the components-and-3-tiers utilities clause to the new capsule; all 8 probes executed green at pin; both Retrieves live via `search_code` (single-result exact-file resolutions); remaining uncited set = excluded-with-reason only (drafts ×4, thincomponents, bumpversion stub) ⇒ English corpus CLOSED at stem level until upstream HEAD advances past dc3d60c.
Pass 6 (2026-08-26, child-agent deepening pass, lane miner-nodebestpractices): HEAD re-verified == pin dc3d60c29d54 (no advance ⇒ no re-index); independent stem census CORRECTED the inventory to 93 English docs (pass-5 regex missed uppercase `LTSrelease.md`, which IS cited) and re-confirmed closure (only 4 drafts uncited); depth audit of the 25 richest docs found the recorded overlap pairs drift-free and three real partials → 1 new capsule-v2 `log-routing-to-stdout` (logrouting.md core contract was name-checked only) + 2 source-confirmed refactors (`return-await-stacktrace-rule` gained anti-pattern #3 async-callback-in-sync-slot + microtask tradeoff + no-return-await history; `transaction-id-correlation` gained the ALS Node-v14/async_hooks restrictions + continuation-local-storage fallback); 59→62 refs; all probes executed green at pin; all Retrieves live via `search_code` (daemon.json / dummy async function / continuation-local-storage needles, English-file line-exact).

## Full view (memory graph)
Revalidate `nodebestpractices` before porting: run `index_status`, `check_index_coverage`, `search_code`, `get_architecture`. Live at last verification (2026-08-26): root `/mnt/hdd/utopia/inspo/frameworks/nodebestpractices` (canonical worktree; project root_path records `/mnt/hdd/utopia/inspo/nodebestpractices`), branch master@dc3d60c (HEAD==base), FULL mode, 6,007 nodes / 6,013 edges, zero parse_partial, 80 image assets excluded-by-design. Doc-shaped graph: 4,632 Section / 661 File / 661 Module nodes; NOTE — BM25 `search_graph` text queries return ZERO on this graph (only 3 shell-script Function nodes carry searchable tokens); use `search_code --pattern <stem>` for retrieval and `check_index_coverage` for freshness. The README is the TL;DR index; section docs carry the deep code examples cited here. Source docs decide shipped claims; no upstream test runner exists (probes are deterministic greps).

## Boundaries
Adopt the practice contracts and their invariants (crash predicate, drain order, KDF floors, external revocation store, two-tier limiter shape, layer-order/cache-bust rules, stateless trio ban, lock→npm-ci chain); adapt library choices (Helmet/joi/rate-limiter-flexible equivalents), thresholds, and tool names to your stack; omit version-pinned specifics that upstream has since superseded (X-XSS-Protection auditor removal, HPKP→Expect-CT deprecation, doc-era size/throughput figures — noted in-capsule), translation READMEs, drafts/, assets/, `.operations/` governance corpus (community authoring workflow — repo-meta only, no Node contract), template.md scaffold, bumpversion.md stub (placeholder "Title here"), thincomponents.md (component doctrine already carried by components-and-3-tiers from pass 1), and generic-tips' language-agnostic items beyond their Node-relevant guards. Coverage caveat: probes are deterministic line-anchored greps against a docs-only repo — no behavioral runner exists upstream.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`aaa-test-structure.md`](./aaa-test-structure.md)
- [`api-error-doc-contract.md`](./api-error-doc-contract.md)
- [`apperror-single-subclass.md`](./apperror-single-subclass.md)
- [`centralized-handler-not-middleware.md`](./centralized-handler-not-middleware.md)
- [`childprocess-shell-injection.md`](./childprocess-shell-injection.md)
- [`commonsecurity-random-compare.md`](./commonsecurity-random-compare.md)
- [`components-and-3-tiers.md`](./components-and-3-tiers.md)
- [`context-aware-output-escaping.md`](./context-aware-output-escaping.md)
- [`dependency-audit-pipeline.md`](./dependency-audit-pipeline.md)
- [`dependency-lock-exact-chain.md`](./dependency-lock-exact-chain.md)
- [`docker-build-cache-ordering.md`](./docker-build-cache-ordering.md)
- [`docker-context-lint-scan-gate.md`](./docker-context-lint-scan-gate.md)
- [`docker-image-slimming-tagging.md`](./docker-image-slimming-tagging.md)
- [`dual-memory-limits.md`](./dual-memory-limits.md)
- [`ephemeral-port-test-bootstrap.md`](./ephemeral-port-test-bootstrap.md)
- [`error-detail-suppression.md`](./error-detail-suppression.md)
- [`eval-family-ban.md`](./eval-family-ban.md)
- [`event-loop-non-blocking.md`](./event-loop-non-blocking.md)
- [`failfast-and-error-flow-tests.md`](./failfast-and-error-flow-tests.md)
- [`five-outcomes-test-coverage.md`](./five-outcomes-test-coverage.md)
- [`four-signals-service-watchlist.md`](./four-signals-service-watchlist.md)
- [`framework-selection-matrix.md`](./framework-selection-matrix.md)
- [`graceful-shutdown-choreography.md`](./graceful-shutdown-choreography.md)
- [`hierarchical-config-contract.md`](./hierarchical-config-contract.md)
- [`injection-proof-data-access.md`](./injection-proof-data-access.md)
- [`jwt-revocation-blacklist.md`](./jwt-revocation-blacklist.md)
- [`log-routing-to-stdout.md`](./log-routing-to-stdout.md)
- [`maintenance-endpoint-gates.md`](./maintenance-endpoint-gates.md)
- [`mature-logger-contract.md`](./mature-logger-contract.md)
- [`monitoring-apm-segmentation.md`](./monitoring-apm-segmentation.md)
- [`multi-stage-build-and-secrets.md`](./multi-stage-build-and-secrets.md)
- [`native-over-userland-lint-gate.md`](./native-over-userland-lint-gate.md)
- [`nock-black-box-isolation.md`](./nock-black-box-isolation.md)
- [`node-direct-bootstrap.md`](./node-direct-bootstrap.md)
- [`node-env-production-contract.md`](./node-env-production-contract.md)
- [`non-root-execution-contract.md`](./non-root-execution-contract.md)
- [`operational-vs-programmer-split.md`](./operational-vs-programmer-split.md)
- [`owasp-control-checklist.md`](./owasp-control-checklist.md)
- [`password-kdf-ladder.md`](./password-kdf-ladder.md)
- [`per-test-data-and-middleware-isolation.md`](./per-test-data-and-middleware-isolation.md)
- [`production-code-habits-checklist.md`](./production-code-habits-checklist.md)
- [`redos-safe-regex-guard.md`](./redos-safe-regex-guard.md)
- [`request-throttling-and-payload-caps.md`](./request-throttling-and-payload-caps.md)
- [`return-await-stacktrace-rule.md`](./return-await-stacktrace-rule.md)
- [`reverse-proxy-offload-ladder.md`](./reverse-proxy-offload-ladder.md)
- [`safe-redirect-whitelist.md`](./safe-redirect-whitelist.md)
- [`schema-validation-gate.md`](./schema-validation-gate.md)
- [`secrets-env-and-npm-publish.md`](./secrets-env-and-npm-publish.md)
- [`security-header-matrix.md`](./security-header-matrix.md)
- [`session-cookie-hardening.md`](./session-cookie-hardening.md)
- [`stateless-phoenix-contract.md`](./stateless-phoenix-contract.md)
- [`static-analysis-quality-ladder.md`](./static-analysis-quality-ladder.md)
- [`static-require-discipline.md`](./static-require-discipline.md)
- [`three-part-test-names.md`](./three-part-test-names.md)
- [`tls-termination-shape.md`](./tls-termination-shape.md)
- [`transaction-id-correlation.md`](./transaction-id-correlation.md)
- [`two-tier-brute-force-limiter.md`](./two-tier-brute-force-limiter.md)
- [`typescript-dosage-rule.md`](./typescript-dosage-rule.md)
- [`unhandled-rejection-funnel.md`](./unhandled-rejection-funnel.md)
- [`untrusted-code-sandbox-ladder.md`](./untrusted-code-sandbox-ladder.md)
- [`uptime-ownership-ladder.md`](./uptime-ownership-ladder.md)
- [`utility-wrap-private-package.md`](./utility-wrap-private-package.md)
