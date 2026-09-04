<!-- capsule-v2 -->
# FabricState assembly ladder — the one place every kernel is constructed, gated, started, and torn down in order

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when a host extension owns a dozen subsystems (mesh, actors, control plane, lifecycle, agents, residency, providers), in what order do they construct/start/close so reloads never leak or double-subscribe?

## Connected graph-selected seam
**Path/Symbol:** `src/fabric-state.ts` whole file (833L): lazy getters that all throw `"Pi Fabric has not initialized"` (:124-194), `initialize(context)` (:196-522), `ensure` (:524-526), `reloadConfig` (:528-537), `registerExternal` (:666-688), `shutdown` (:690-721), `#closeInternal` (:741-767), `#publishCompactEvent` (:726-739), module-level `deepAssign` (:818-833), `lifecycleMetadata`/`scalarMetadata` (:770-807).
**Signature:** `async initialize(context: ExtensionContext)` — idempotent via `await this.#closeInternal()` FIRST; `ensure(context)` re-initializes only when uninitialized OR cwd changed.
**Data Shape:** every kernel held as `#field | undefined`; `initialized === Boolean(this.#execution)` — the execution service is constructed LAST and is THE readiness signal.

### Decisive source
```ts
const ownsPersistentActorRegistry =
  identity.kind === "main" &&
  !enforceSchema &&
  projectTrusted &&
  this.#config.mesh.enabled;
// ...
const agentConfig = enforceSchema ? { ...this.#config.agents, enabled: false } : this.#config.agents;
// ...
this.enforceSchema ? { ...this.#config.mesh, enabled: false } : this.#config.mesh,
```

**Flow (construction order is the contract):** reset (`#closeInternal`, `prewalk.cancel`, `activity.reset`, approvals clear) → load config with `projectTrusted` → ActionRegistry(+result proxy) → mode-derived flags (`enforceSchema`, `effectiveFullCodeMode = fullCodeMode || enforceSchema`) → register providers conditionally (pi-tools only if effectiveFullCodeMode; captured-tools provider only if full-code AND capture.enabled AND NOT enforce; mcp always; mesh+state only when mesh.enabled) → resolve identity + MainAgentController → MeshStore at `PI_FABRIC_MESH_ROOT ?? config.mesh.root resolved against PI_FABRIC_PROJECT_ROOT ?? cwd` defaulting to `<root>/.pi/fabric/mesh` → ParticipantDirectory + ControlPlane with `hostId = main ? mainAgentId : runtime:<sessionId>` → SchemaController → CompactController → AgentManager (agents FORCE-DISABLED under enforce) → ActorManager (persistent registry only when the four-way gate holds) → LifecycleBroker (disabled under enforce) → GlobalActorRegistry → ResidencyClient ONLY when owning persistent actors, with structuredClone'd config snapshots and import.meta-relative worker/extension paths → participant sources registered (root self-record only when main.local) + refresh subscriptions → AgentsProvider → `control.start(handler)` → `participants.start()` with best-effort catch (warn + notify, heartbeat retries) → lifecycle/residency start → agentsProvider registered → memory provider if enabled → EXTERNAL providers from the pre-init map → FabricExecutionService LAST → emit discovery event. Shutdown mirrors it exactly: participants.quiesce (errors swallowed) → lifecycle.close → control.close → residency.close → registry.close in try / participants.close in FINALLY → null every field → reset activity/prewalk.
**Invariant:** (1) `#closeInternal()` runs BEFORE any re-init work so a session_start after session_shutdown can never double-register or leak subscriptions. (2) Enforce schema mode force-disables agents, mesh-driven actor dispatch, and lifecycle publishing by passing SHALLOW CLONES with `enabled:false` — the original config object is never mutated, and each subsystem sees one consistent snapshot. (3) The four-way `ownsPersistentActorRegistry` gate (main identity ∧ ¬enforce ∧ trusted project ∧ mesh.enabled) decides BOTH actor persistence AND ResidencyClient existence — they live and die together. (4) Initial mesh publish failure is NON-FATAL: warn + UI notice, heartbeat keeps retrying — a flaky mesh must not block host startup. (5) External providers registered before initialization are buffered in `#externalProviders` and flushed during initialize; reserved names (pi/mcp/agents/mesh/extensions/fabric/schema/state/memory/compact) are rejected loudly. (6) `reloadConfig` deep-assigns fresh config into the LIVE object but pins `schema.mode` to its current value first — runtime mode flips are impossible without full re-init. (7) Compaction events publish best-effort to topic `fabric.compact` with a silent catch — a FULL event log must never break host compaction. (8) Background completion notices cap summaries at 8k chars (`BACKGROUND_COMPLETION_MAX_CHARS`) before `sendMessage`.
**Probe:** `tests/extension-shutdown.test.ts:9` ("unsubscribes shared provider listeners across reloads" — 3 × init/shutdown cycles keep exactly ONE provider listener alive). `tests/config.test.ts:160` ("forces QuickJS in Schema enforce mode") + `:380` ("forces fabric_exec to be the only capture visibility exception in enforce mode") pin the enforce-mode gating this ladder implements. `tests/main-agent.test.ts` exercises `resolveFabricIdentity` feeding step 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricState initialize shutdown ensure reloadConfig registerExternal ownsPersistentActorRegistry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strict construct→gate→start→(mirror-order)close ladder with an execution-service-as-readiness-signal and clone-with-enabled:false feature gating; adapt member names. Porters get this wrong by starting subsystems mid-construction or mutating shared config for gating — both cause reload leaks the upstream shutdown test explicitly pins.
