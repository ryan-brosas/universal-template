<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Coolify: Self-hosted deploy orchestrator foundation

## Use this for
Use when porting a PaaS-style deployment orchestrator: a DB-backed deployment queue with admission control, a 5k-line build-pack state machine that drives remote Docker hosts over SSH, rolling updates with health-gated cutover, and cron-dedup scheduled jobs. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./deployment-queue-admission.md` — How does Coolify admit, skip, and drain deployments without double-running one?
- `./deployment-status-state-machine.md` — How do status transitions stay terminal-once and race-free against user cancels?
- `./buildpack-router.md` — What is the dispatch order from job start through builder prep to the right build pack?
- `./env-var-pipeline.md` — Which env vars exist at build time vs runtime, and in what order must .env be written?
- `./rolling-update-ordering.md` — Why does start-before-stop plus health-gate make zero-downtime deploys safe?
- `./container-cleanup-timeout.md` — How are stop/remove failures contained so cleanup never fails a good deployment?
- `./remote-command-lifecycle.md` — How does one SSH command become logs, saved outputs, retries, and cancellation?
- `./ssh-multiplexing-lock.md` — How is the per-server SSH master socket kept alive and lock-safe across workers?
- `./ssh-retry-classification.md` — Which SSH errors retry with backoff, and which fail immediately?
- `./sudo-transformation.md` — How do commands get sudo-prefixed for non-root servers without breaking pipelines?
- `./scheduled-cron-dedup.md` — How do scheduled backups/tasks fire exactly once per cron window despite chunked polling?
- `./git-commit-resolution.md` — How is the deploy commit resolved from ls-remote, and when does the helper container restart mid-deployment?
- `./server-check-selfhealing.md` — How does the periodic server job converge containers, sentinel, log drain, and proxy state?
- `./image-naming-push.md` — How are build/production image names derived per pack, preview, and registry config?
- `./docker-label-comma-parsing.md` — How does label parsing survive commas inside values and value-less labels?
- `./team-broadcast-config-refresh.md` — How does saving a required service variable refresh the config page in every open tab?
- `./livewire-failure-toast-gestures.md` — How do gateway failures toast exactly once per user action while background polling stays silent?
- `./proxy-status-restart-vs-update.md` — Why do pending proxy config changes and available proxy updates need different labels?
- `./template-contract-compose-twin.md` — What makes a one-click service template valid, and why does it exist in two registry dialects?
- `./proxy-network-reconcile-all-containers.md` — Why must proxy network discovery include stopped containers?
- `./dev-failure-preview-route.md` — How is a fault-injection endpoint shipped for failure-UX tests without ever mounting in production?

## Capsule map
- **Deployment queue admission** — `deployment-queue-admission`: dedupe on (application, commit, PR, tag) + server queue limit; drain loop advances QUEUED rows via `next_queuable`.
- **Status state machine** — `deployment-status-state-machine`: terminal states immutable; cancel = sentinel code 69420; every transition calls `queue_next_deployment`.
- **Build-pack router** — `buildpack-router`: ordered `decide_what_to_do()` dispatch; BuildKit/buildx capability probe before any build.
- **Env var pipeline** — `env-var-pipeline`: build-time env excludes volatile vars (`SOURCE_COMMIT`, `COOLIFY_CONTAINER_NAME`) to protect Docker cache; runtime .env written AFTER build; preview falls back to prod values only when previews configured.
- **Rolling update** — `rolling-update-ordering`: start new → health-check → stop old; unsupported modes force stop-first; unhealthy new version triggers rollback + FAILED.
- **Container cleanup** — `container-cleanup-timeout`: `docker rm -f` wrapped with shell `timeout`, marker string detected in output schedules delayed `RemoveContainerJob`.
- **Remote command lifecycle** — `remote-command-lifecycle`: per-command cancellation refresh, redaction of shown-once secrets, JSON log appends with order+batch, `save:` output capture.
- **SSH multiplexing** — `ssh-multiplexing-lock`: ControlMaster socket per server uuid, cache lock around establishment, retirement markers prevent PID reuse kills.
- **SSH retry classification** — `ssh-retry-classification`: substring table of retryable transport errors; exponential backoff capped by config; non-transport errors throw at once.
- **Sudo transformation** — `sudo-transformation`: keyword-aware sudo prefixing, complex pipes wrapped as `sudo bash -c '...'`, mkdir ownership for coolify paths; upstream `startSwith` typo regression documented.
- **Scheduled cron dedup** — `scheduled-cron-dedup`: frozen execution time, per-key last-dispatch cache, `previousDue > lastDispatched` decides firing; interleaved backup/task chunks.
- **Git commit resolution** — `git-commit-resolution`: exact-refspec ls-remote with tab-anchored SHA extraction; builder restart when SOURCE_COMMIT becomes real for build secrets.
- **Server check self-healing** — `server-check-selfhealing`: convergent tick reconciling container rows/sentinel/log-drain/proxy; timeouts increment `unreachable_count` instead of failing.
- **Image naming & push** — `image-naming-push`: `<uuid|registry>:<sha128>` naming, pr-N tags sanitized from commit, push forced-fail matrix by swarm/build-server/additional-servers.
- **Docker label parsing** — `docker-label-comma-parsing`: comma-split before limit-2 equals-split; value-less tokens yield no entry; array passthrough.
- **Team broadcast refresh** — `team-broadcast-config-refresh`: dynamic `getListeners()` embeds team id; required-service-var save broadcasts `ApplicationConfigurationChanged`; one handler serves local + Echo buses.
- **Failure toast gestures** — `livewire-failure-toast-gestures`: send-time gesture-window classification (2s), strict-> per-gesture toast latch, always-preventDefault on infra statuses; 9/9 node --test at pin.
- **Proxy status labels** — `proxy-status-restart-vs-update`: match-arm precedence pending>update for text; aggregate boolean unchanged for coloring; design test pins arm strings.
- **Template contract** — `template-contract-compose-twin`: directive headers, FQDN-vs-URL env dialects, generated-credential placeholders, base64 twin registries with deliberate dialect split pinned by test.
- **Proxy network reconcile** — `proxy-network-reconcile-all-containers`: label-scoped status-independent discovery (`docker ps -a`) + existence-guarded idempotent connects.
- **Dev failure preview** — `dev-failure-preview-route`: env-gated route + strict status allowlist abort + realistic gateway HTML body mirrored to JS status set.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Coolify (Apache-2.0), `main@981163973b4b33726e378d7dcf9812459efc6f60` (pass-1 pin `379abb252621f34b318190bd49b614aed9818716` + 7 drift commits, 2026-08-24); Codebase Memory project `ext-coolify` re-indexed in place at the new head (full mode, 38,931 nodes / 211,192 edges; blade/CSS parse_partial files listed in index_status are excluded-by-design noise — all cited PHP/JS paths coverage-clean).

## Full view (memory graph)
Revalidate `ext-coolify` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 plane works well here (function nodes carry tokens); bootstrap/helpers functions are searchable directly (e.g. `next_queuable`). Note: `vendor/laravel/framework` sources are not indexed — Stringable macro claims were verified by absence-of-definition sweep + upstream git archaeology instead.

## Boundaries
Adopt the queue/state-machine contracts, env-var build-vs-runtime split, rolling-update ordering, cron dedup algorithm, SSH command/retry/mux plumbing, label-parsing and gesture/toast classification as pure behavior. Adapt Laravel-specific wiring (Horizon queues, Eloquent models, Cache/Redis locks, Livewire/Echo event names) to your host stack. omit Coolify product surfaces: Stripe/cloud gating, Sentinel/proxy management internals, GitHub App source integrations, and the specific helper-image toolchain; template YAML bodies beyond the contract capsule are catalog data, not seams.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`buildpack-router.md`](./buildpack-router.md)
- [`container-cleanup-timeout.md`](./container-cleanup-timeout.md)
- [`deployment-queue-admission.md`](./deployment-queue-admission.md)
- [`deployment-status-state-machine.md`](./deployment-status-state-machine.md)
- [`dev-failure-preview-route.md`](./dev-failure-preview-route.md)
- [`docker-label-comma-parsing.md`](./docker-label-comma-parsing.md)
- [`env-var-pipeline.md`](./env-var-pipeline.md)
- [`git-commit-resolution.md`](./git-commit-resolution.md)
- [`image-naming-push.md`](./image-naming-push.md)
- [`livewire-failure-toast-gestures.md`](./livewire-failure-toast-gestures.md)
- [`proxy-network-reconcile-all-containers.md`](./proxy-network-reconcile-all-containers.md)
- [`proxy-status-restart-vs-update.md`](./proxy-status-restart-vs-update.md)
- [`remote-command-lifecycle.md`](./remote-command-lifecycle.md)
- [`rolling-update-ordering.md`](./rolling-update-ordering.md)
- [`scheduled-cron-dedup.md`](./scheduled-cron-dedup.md)
- [`server-check-selfhealing.md`](./server-check-selfhealing.md)
- [`ssh-multiplexing-lock.md`](./ssh-multiplexing-lock.md)
- [`ssh-retry-classification.md`](./ssh-retry-classification.md)
- [`sudo-transformation.md`](./sudo-transformation.md)
- [`team-broadcast-config-refresh.md`](./team-broadcast-config-refresh.md)
- [`template-contract-compose-twin.md`](./template-contract-compose-twin.md)
