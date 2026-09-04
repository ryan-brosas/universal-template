<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Nexus Repository Foundation

## Use this for
Building or porting server-side infrastructure contracts proven at Sonatype scale: a durable job scheduler layered over Quartz with freeze/pause semantics and cross-node replication; thread-scoped transactional sessions with exception-classified commit/retry/swallow and jittered backoff; a capability framework that manages plugin-object lifecycle (per-object state machine, event-driven activation gating, validity self-destruction, HA sync, secret and schema handling); blob-store mechanics covering pure-function ID→path layout, crash-safe file writes, two-phase soft delete, S3 multipart/parallel copy, group fill policies, and bucket preparation; cookie-session security filters (JWT + anti-CSRF); and an interceptor-chain request router that format plugins extend without touching core code. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./task-activation-freeze.md` — how a scheduler pauses for maintenance without losing its queue, and which tasks survive a freeze.
- `./quartz-task-future.md` — the Future/cancel ladder that never interrupts unless the caller insists.
- `./task-lifecycle-listener.md` — the per-job listener that owns the RUNNING→WAITING/DONE state machine and last-run persistence.
- `./task-blocking-mayblock.md` — same-type mutual exclusion with blob-store-scoped refinement.
- `./cluster-event-replication.md` — event-driven multi-node scheduler sync that reuses Quartz as the transport.
- `./jwt-cookie-session.md` — stateless NXSESSIONID cookie sessions with revocation checks and refresh-on-verify.
- `./anti-csrf-double-submit.md` — cookie-to-header token validation with Sec-Fetch-Site pre-filter.
- `./authz-realm-role-ladder.md` — the authorization-only realm that turns principals into roles and rejects disabled-realm users.
- `./role-tree-permission-resolution.md` — cycle-safe role-tree expansion into permissions with a bounded negative cache.
- `./realm-manager-ordered-activation.md` — persisted ordered realm activation with the authorizing realm forced last.
- `./exception-catching-authorizer.md` — per-realm exception containment that keeps deny-by-default intact.
- `./anonymous-subject-gating.md` — request-scoped anonymous subject swap driven by replicated config.
- `./default-role-realm-grant.md` — baseline role injected at authorization time for every non-anonymous principal.
- `./jexl-sandbox-engine.md` — hardened JEXL engine + uberspect whitelist that make constructors/writes/arbitrary methods unresolvable.
- `./selector-factory-validate-ladder.md` — the shared-engine type switch that validates and instantiates jexl/csel selectors with field-level violations.
- `./csel-ast-whitelist-validation.md` — deny-by-default AST visitor defining the exact translatable CSEL grammar.
- `./csel-to-sql-parameterized-translation.md` — AST→parameterized WHERE compilation with null-safe `!=`, anchored regex, and an injection-proof builder.
- `./variable-source-resolver-chain.md` — ordered namespaced resolver chain feeding a lazy memoized read-only JEXL context.
- `./selector-manager-crud-cache-coherence.md` — soft compile/browse caches, four-event invalidation ladder, and privilege-scan referential-integrity delete guard.
- `./browse-active-permitted-selectors.md` — metadata-only reverse lookup of which selectors apply to the current user via role-tree expansion.
- `./leading-slash-path-normalization.md` — bounded path-regex leading-slash rewriting (fully tested; production wiring currently passes false).
- `./view-router-chain.md` — route matching plus the mutable ListIterator handler chain (insert/replay semantics).
- `./security-handler-once.md` — authorize exactly once per request even across group-repository fan-out.
- `./exception-handler-read-only.md` — exception→HTTP-status mapping including frozen/read-only detection by class name.
- `./handler-contributor-extension.md` — the plugin seam that injects handlers into every route at dispatch time.
- `./recipe-assembly.md` — the recipe pattern: format × type ⇒ facet set + router wiring per repository.
- `./rest-resource-layering.md` — thin annotation-guarded REST resources with a precise HTTP-status ladder.
- `./unitofwork-session-scoping.md` — thread-local unit-of-work stack: fresh-vs-batched sessions, pause/resume around event broadcasts.
- `./transactional-commit-retry-ladder.md` — the exception-class-driven commit/retry/swallow matrix that never loses the business cause.
- `./retry-controller-backoff.md` — jittered slot-doubling backoff with an hourly excessive-retries ring.
- `./capability-lifecycle-state-machine.md` — the NEW→DISABLED→ENABLED→ACTIVE per-object state machine with throw-by-default illegal transitions and latched callback failures.
- `./capability-activation-condition-handler.md` — bind-time composition of a capability's own condition with system-health gates (null⇒always, exception⇒never).
- `./capability-validity-condition-handler.md` — two-phase validity gating that self-destructs a capability when its validity condition breaks.
- `./capability-registry-ha-sync.md` — cluster CRUD replication via storage events applied by a single-thread executor that re-reads the database as truth.
- `./capability-secret-lifecycle.md` — encrypt-on-write / reuse / prune pairing for config secrets, decrypted only at consumption.
- `./capability-schema-versioning.md` — version-stamped plugin config with convert-on-load write-back migration and mode-grouped validation strictness.
- `./capability-condition-dsl.md` — reactive AND/OR/NOT condition tree: idempotent bind/release, edge-triggered events, identity-filtered recomposition.
- `./blob-id-location-strategies.md` — prefix-tagged ID grammar mapping blob IDs to paths with no central index.
- `./file-blobstore-create-delete.md` — crash-safe temp+rename writes and two-phase soft delete on a filesystem.
- `./s3-multipart-upload-copy.md` — size-adaptive multipart upload and parallel server-side copy with abort-on-failure.
- `./blobstore-group-fill-policies.md` — policy-routed writes to one member, search-based reads, delete fan-out.
- `./blobstore-get-retry-ladder.md` — classify-before-retry reads that never poll away a confirmed soft delete.
- `./s3-bucket-preparation-ladder.md` — cached validate/create bucket ladder with ownership and access-denied typing.
- `./ui-plugin-descriptor-duality.md` — how UI-contributing modules declare assets across the legacy ExtJS and modern React descriptor SPIs without a registry.
- `./rapture-web-resource-bundle.md` — assembling index/bootstrap/app resources from descriptors with a prod/debug mode switch and cache busting.
- `./uiutil-classpath-asset-resolution.md` — filename→web-path resolution for assets scattered across plugin jars.
- `./two-phase-component-scan.md` — why every plugin module may reuse simple bean names: FQCN child-context scanning after boot.
- `./lifecycle-phase-machine.md` — ordered subsystem start/stop phases, TASKS-failure tolerance, bounce, and the startup-phase cap.
- `./edition-selection-ladder.md` — single-edition boot selection by priority with fail-loud fallback.
- `./distribution-overlay-assembly.md` — how the Maven overlay produces the distribution layout and the defaults-vs-data-dir precedence contract.
- `./script-create-gate.md` — default-off script creation gating that deliberately leaves delete/run available.
- `./script-rest-contract.md` — script API status ladder (404/410/400) and per-name permission shape.
- `./state-poll-hash-delta.md` — hash-based delta polling protocol for UI state over plain HTTP.

## Capsule map
- **Task scheduling** — `task-activation-freeze`, `quartz-task-future`, `task-lifecycle-listener`, `task-blocking-mayblock`, `cluster-event-replication`: lifecycle-phase pause/resume with RUN_WHEN_FROZEN exemptions, non-interrupting-first cancel ladder with monotonic run-state transitions, per-job-listener state machine persisting last-run state into job data, same-type blocking refined per blob store, and cluster-wide job/trigger replication via self-addressed events that drive Quartz's own signal paths.
- **Web security** — `jwt-cookie-session`, `anti-csrf-double-submit`: HMAC-signed stateless session cookies carrying user/realm/session-id claims with DB-backed revocation + audit-on-replay, and double-submit CSRF tokens gated to session-authenticated unsafe methods with Sec-Fetch-Site metadata pre-filtering.
- **Authorization core** — `authz-realm-role-ladder`, `role-tree-permission-resolution`, `realm-manager-ordered-activation`, `exception-catching-authorizer`, `anonymous-subject-gating`, `default-role-realm-grant`: an authorize-only Shiro realm whose role ladder rejects disabled-realm principals behind a per-principal permission cache; iterative visited-set role-tree expansion over three caches (soft permission, soft role-result, bounded role-not-found); stored ordered realm activation where remove-then-add pins NexusAuthorizingRealm last and remote config events apply without re-saving; realm-by-realm exception containment preserving deny-by-default; request-scoped anonymous subject binding keyed on the AnonymousPrincipalCollection type marker; and authorization-time default-role injection for external users.
- **Content selectors** — `jexl-sandbox-engine`, `selector-factory-validate-ladder`, `csel-ast-whitelist-validation`, `csel-to-sql-parameterized-translation`, `variable-source-resolver-chain`, `selector-manager-crud-cache-coherence`, `browse-active-permitted-selectors`, `leading-slash-path-normalization`: a sandboxed JEXL engine (null-returning uberspect, 9-method receiver-typed whitelist) hosting user expressions behind one shared-engine factory whose validate/create type switch wraps failures as field violations; CSEL defined by a deny-by-default AST whitelist ({format,path} identifiers, quote-free literals, compile-checked regex) and compiled to parameterized SQL where literals always bind and `!=`/`=~` get explicit three-valued-logic/anchoring repairs; variables flow through an ordered namespaced resolver chain into a lazy memoized read-only context; the manager layers soft compile/browse caches invalidated by four local+remote event types, blocks deletes via a live privilege reference scan, and answers "which selectors apply to me" from role-tree expansion without evaluating anything; leading-slash path rewriting ships fully tested but toggled off at its single call site.
- **Repository view pipeline** — `view-router-chain`, `security-handler-once`, `exception-handler-read-only`, `handler-contributor-extension`, `recipe-assembly`: first-match route dispatch into a replayable mutable handler chain, group-fan-out authorization memoized per request, typed exception→response mapping with read-only-mode detection, reverse-order contributed-handler injection guarded by a context marker, and declarative recipe composition as the plugin contract.
- **API layering** — `rest-resource-layering`: annotation-guarded thin resources over domain services with a precise HTTP-status translation discipline.
- **Transactional work units** — `unitofwork-session-scoping`, `transactional-commit-retry-ladder`, `retry-controller-backoff`: a thread-local three-scope session stack (fresh-per-op, shared batch, store-local) with pause/resume around out-of-scope callbacks; commit/retry/swallow decided by exception class with the original cause always preserved or suppressed-attached; and bounded jittered backoff whose slot count doubles per attempt while an hourly ring counts near-exhaustion sequences.
- **Capability framework** — `capability-lifecycle-state-machine`, `capability-activation-condition-handler`, `capability-validity-condition-handler`, `capability-registry-ha-sync`, `capability-secret-lifecycle`, `capability-schema-versioning`, `capability-condition-dsl`: a per-object NEW→DISABLED→ENABLED→ACTIVE state machine that latches callback failures without blocking transitions, event-driven activation gating composed from capability + system-health conditions with mirrored fail-closed/fail-open fallbacks, validity-breach auto-removal, single-thread-applier cluster sync that re-reads storage as truth, secret-ID persistence with reuse detection and paired pruning, versioned config migration at load time, and the reactive condition DSL those gates are built from.
- **Blob stores** — `blob-id-location-strategies`, `file-blobstore-create-delete`, `s3-multipart-upload-copy`, `blobstore-group-fill-policies`, `blobstore-get-retry-ladder`, `s3-bucket-preparation-ladder`: pure-function ID→path resolution (tmp$/path$ prefixes + two-tier hash fan-out), temp-write/atomic-move publication with bounded collision re-minting and soft-delete-with-parked-attributes, size-adaptive S3 multipart upload plus parallel sorted-part copy with abort-on-failure, group fill-policy routing memoized into a located-blobs cache, classify-before-retry reads, and cached bucket validation with ownership/access-denied error typing.
- **Plugin & UI extension system** — `ui-plugin-descriptor-duality`, `rapture-web-resource-bundle`, `uiutil-classpath-asset-resolution`: dual ExtJS/React descriptor SPIs aggregated by constructor-injected lists under a jakarta @Priority load ladder, template-generated index/bootstrap/app resources whose script order, {mode} switch, `_v&_e&_c` cache suffix, and SNAPSHOT cache-kill are all pinned by test, and classpath-scan filename→web-path resolution with the `/static` substring cut contract.
- **Boot & wiring** — `two-phase-component-scan`, `lifecycle-phase-machine`, `edition-selection-ladder`, `distribution-overlay-assembly`: entrypoint-first then FQCN-named child-context scanning that lets every plugin reuse simple bean names, an 11-phase ordinal start/stop machine where only TASKS tolerates component failure and `nexus.lifecycle.startupPhase` caps boot below full climb, single-edition selection by priority sort that fails loudly when nothing is active, and the overlay-produced distribution layout whose defaults-yield-to-data-dir precedence deployments depend on.
- **Scripting subsystem** — `script-create-gate`, `script-rest-contract`: default-deny script creation (`nexus.scripts.allowCreation:false`) gating only create/update while delete/run stay available, mapped by the REST layer to 410 GONE; BREAD resources mixing annotation perms for collection ops with per-name programmatic permissions (`nexus:script:<name>:<action>`) and a 404/410/400 status ladder.
- **UI state protocol** — `state-poll-hash-delta`: client-sent hash map drives SHA1-of-Gson delta responses where null means "unchanged or gone", contributor failures are isolated per poll, and clustered boots prefix `serverId` with `ignore.`.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Nexus Repository (Sonatype), EPL-1.0, `main@0a8a425daa4b37e924ca11e4637a41afce7b115c`; Codebase Memory project `nexus-public`. Pass 2 (2026-08-23) re-verified HEAD unchanged and extended coverage to `nexus-transaction` (whole component incl. its ~25-test matrix), the capability plane (`nexus-capability` API + `nexus-core` internal registry/reference/handlers), and `nexus-blobstore{,-api,-file,-s3}` — all newly cited paths `no_recorded_issue`/`metadata_match` via `check_index_coverage`. Pass 3 (2026-08-24) mined the plugin/boot/UI-extension plane at the SAME pin: `UiPluginDescriptor` duality, Rapture web-resource bundle (+ its direct test), UiUtil, two-phase component scan, lifecycle phase machine, edition selection, script create-gate + REST contract, state poll hash-delta, and distribution overlay — 10 capsule-v2 added (29→39), 12 newly cited paths coverage-checked clean. ERRATUM (2026-08-23 late): pass 2's twin lane split the capability plane into the deeper 7-capsule framework above, superseding the earlier 3-capsule set (`capability-state-machine`, `capability-activation-conditions`, `capability-registry-cluster-sync`) whose files were lost to an aborted rebase; the surviving 12 transaction/blobstore capsules were restored verbatim from orphaned commit `8cb8257a` after HEAD cited them without the files existing anywhere. Pass 4 (2026-08-25, SAME pin) mined the security authorization core at HEAD==base: AuthorizingRealmImpl role ladder + per-principal cache, RolePermissionResolverImpl cycle-safe tree walk with bounded negative cache, RealmManagerImpl ordered activation + force-last authorizer + remote-event apply, ExceptionCatchingModularRealmAuthorizer deny-by-default containment, AnonymousFilter/AnonymousManagerImpl type-marker subject gating, DefaultRoleRealm grant — 6 capsule-v2 added (39→45); all 15 newly cited paths verified `no_recorded_issue`/`metadata_match` via `check_index_coverage`; direct tests named but NOT executed — no JDK/Maven on PATH (runner block recorded in verification.md).

Pass 5 (2026-08-26, SAME pin) mined the content-selector subsystem at HEAD==base: SandboxJexlUberspect/JexlEngine sandbox, SelectorFactory validate/create ladder, CselValidator deny-by-default grammar, DatastoreCselToSql+SelectorSqlBuilder parameterized SQL push-down (null-safe `!=`, anchored `=~`, bind-everything literals), VariableSource resolver chain + lazy JEXL context, SelectorManagerImpl soft caches with four-event invalidation and privilege-scan delete guard, browseActive role-tree reverse lookup, LeadingSlash transformers (tested; production flag false) — 8 capsule-v2 added (45→53); all 20 newly cited paths verified `no_recorded_issue`/`metadata_match` via `check_index_coverage`; direct tests named but NOT executed — no JDK/Maven on PATH (runner block persists).

## Full view (memory graph)
Revalidate `nexus-public` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Live at last verification (2026-08-26): root `$REFERENCE_ROOT/nexus-public` (canonical; worktree path `$REFERENCE_ROOT/reference/nexus-public` reported by index_status), branch `main@0a8a425d` (HEAD==base, zero drift), status ready, FULL mode, 71,282 nodes / 406,602 edges, graph generation `2026-08-23T00:14:23Z`; 16 labels incl. 25,126 Methods / 7,050 Classes / 384 Routes; parse_partial limited to SCSS/CSS/test-fixture noise (no production Java gaps); 1,507 static assets excluded by design; all 12 pass-3-cited paths verified `no_recorded_issue` + `metadata_match`; adversarial wrong-project retrieval (`ext-lemmy`) returns zero hits for this foundation's queries; pass 4 re-confirmed pin/counts and all 15 cited paths `no_recorded_issue`+`metadata_match`; pass 5 re-confirmed pin/counts and verified all 20 newly cited selector paths (14 main + 6 test) `no_recorded_issue`+`metadata_match` (coverage generation_matches=true throughout). Source and direct tests decide shipped claims.

## Boundaries
Adopt the scheduler lifecycle/cancel/blocking contracts, the thread-scoped transaction and retry/backoff semantics, the capability state-machine/gating/sync/secret/schema contracts, the blob-store layout/soft-delete/multipart/group mechanics, the cookie-session and CSRF filter shapes, the router/handler-chain mechanics, the descriptor-priority aggregation + generated-resource contracts, the phase/error-policy/startup-cap boot machine, the default-off script create-gate with its 404/410/400 REST ladder, and the hash-delta state poll protocol; adapt Spring/Shiro/JAX-RS wiring, Guava EventBus fan-out, AWS SDK v2 client types, OrientDB-era artifacts, and the datastore layer to your host; omit the ExtJS/Rapture frontend internals beyond the descriptor/bundle/state contracts captured here, SCSS/static assets, format-specific content logic beyond the raw recipe exemplar, closed-source Pro plugin machinery (no PluginManager/OSGi layer exists in this OSS tree), and product REST resources except as layering examples.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`anonymous-subject-gating.md`](./anonymous-subject-gating.md)
- [`anti-csrf-double-submit.md`](./anti-csrf-double-submit.md)
- [`authz-realm-role-ladder.md`](./authz-realm-role-ladder.md)
- [`blob-id-location-strategies.md`](./blob-id-location-strategies.md)
- [`blobstore-get-retry-ladder.md`](./blobstore-get-retry-ladder.md)
- [`blobstore-group-fill-policies.md`](./blobstore-group-fill-policies.md)
- [`browse-active-permitted-selectors.md`](./browse-active-permitted-selectors.md)
- [`capability-activation-condition-handler.md`](./capability-activation-condition-handler.md)
- [`capability-condition-dsl.md`](./capability-condition-dsl.md)
- [`capability-lifecycle-state-machine.md`](./capability-lifecycle-state-machine.md)
- [`capability-registry-ha-sync.md`](./capability-registry-ha-sync.md)
- [`capability-schema-versioning.md`](./capability-schema-versioning.md)
- [`capability-secret-lifecycle.md`](./capability-secret-lifecycle.md)
- [`capability-validity-condition-handler.md`](./capability-validity-condition-handler.md)
- [`cluster-event-replication.md`](./cluster-event-replication.md)
- [`csel-ast-whitelist-validation.md`](./csel-ast-whitelist-validation.md)
- [`csel-to-sql-parameterized-translation.md`](./csel-to-sql-parameterized-translation.md)
- [`default-role-realm-grant.md`](./default-role-realm-grant.md)
- [`distribution-overlay-assembly.md`](./distribution-overlay-assembly.md)
- [`edition-selection-ladder.md`](./edition-selection-ladder.md)
- [`exception-catching-authorizer.md`](./exception-catching-authorizer.md)
- [`exception-handler-read-only.md`](./exception-handler-read-only.md)
- [`file-blobstore-create-delete.md`](./file-blobstore-create-delete.md)
- [`handler-contributor-extension.md`](./handler-contributor-extension.md)
- [`jexl-sandbox-engine.md`](./jexl-sandbox-engine.md)
- [`jwt-cookie-session.md`](./jwt-cookie-session.md)
- [`leading-slash-path-normalization.md`](./leading-slash-path-normalization.md)
- [`lifecycle-phase-machine.md`](./lifecycle-phase-machine.md)
- [`quartz-task-future.md`](./quartz-task-future.md)
- [`rapture-web-resource-bundle.md`](./rapture-web-resource-bundle.md)
- [`realm-manager-ordered-activation.md`](./realm-manager-ordered-activation.md)
- [`recipe-assembly.md`](./recipe-assembly.md)
- [`rest-resource-layering.md`](./rest-resource-layering.md)
- [`retry-controller-backoff.md`](./retry-controller-backoff.md)
- [`role-tree-permission-resolution.md`](./role-tree-permission-resolution.md)
- [`s3-bucket-preparation-ladder.md`](./s3-bucket-preparation-ladder.md)
- [`s3-multipart-upload-copy.md`](./s3-multipart-upload-copy.md)
- [`script-create-gate.md`](./script-create-gate.md)
- [`script-rest-contract.md`](./script-rest-contract.md)
- [`security-handler-once.md`](./security-handler-once.md)
- [`selector-factory-validate-ladder.md`](./selector-factory-validate-ladder.md)
- [`selector-manager-crud-cache-coherence.md`](./selector-manager-crud-cache-coherence.md)
- [`state-poll-hash-delta.md`](./state-poll-hash-delta.md)
- [`task-activation-freeze.md`](./task-activation-freeze.md)
- [`task-blocking-mayblock.md`](./task-blocking-mayblock.md)
- [`task-lifecycle-listener.md`](./task-lifecycle-listener.md)
- [`transactional-commit-retry-ladder.md`](./transactional-commit-retry-ladder.md)
- [`two-phase-component-scan.md`](./two-phase-component-scan.md)
- [`ui-plugin-descriptor-duality.md`](./ui-plugin-descriptor-duality.md)
- [`uiutil-classpath-asset-resolution.md`](./uiutil-classpath-asset-resolution.md)
- [`unitofwork-session-scoping.md`](./unitofwork-session-scoping.md)
- [`variable-source-resolver-chain.md`](./variable-source-resolver-chain.md)
- [`view-router-chain.md`](./view-router-chain.md)
