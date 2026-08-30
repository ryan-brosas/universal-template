<!-- capsule-v2 -->
# Auto-mode gate ladder — transform-not-snapshot against the async-await mode race

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** An async feature-gate check (network fetch) decides whether a privileged mode is available — how do you apply its result without clobbering mode changes the user made while awaiting, and how do circuit breakers interact with CLI intent?

## Path/Symbol
**Path/Symbol:** `src/utils/permissions/permissionSetup.ts` — `AutoModeGateCheckResult` transform type (:1035-1043), `verifyAutoModeGateAccess` (:1078-1260), `kickOutOfAutoIfNeeded` (:1190-1226), `initialPermissionModeFromCLI` ordered-mode priority (:689-811), `getAutoModeEnabledStateIfCached` Symbol sentinel (:1335-1352), `isAutoModeGateEnabled` sync triple-check (:1283-1288); `src/utils/permissions/bypassPermissionsKillswitch.ts` — run-once checks applying transforms on CURRENT context (:19-55, :74-117).
**Signature:** `verifyAutoModeGateAccess(currentContext, fastMode?) → Promise<{updateContext: (ctx) => ToolPermissionContext, notification?}>`.
**Data Shape:** Gate inputs: GrowthBook `tengu_auto_mode_config.enabled ∈ {'enabled','disabled','opt-in'}` (default 'disabled'), settings `disableAutoMode`, model support, `disableFastMode` breaker; module-singleton flags (`autoModeActive`, `autoModeCircuitBroken`, `autoModeFlagCli`) in autoModeState.ts.

### Decisive source
```ts
// Transform function (not a pre-computed context) so callers can apply it
// inside setAppState(prev => ...) against the CURRENT context. Pre-computing
// the context here captured a stale snapshot: the async GrowthBook await
// below can be outrun by a mid-turn shift-tab, and returning
// { ...currentContext, ... } would overwrite the user's mode change.
updateContext: (ctx: ToolPermissionContext) => ToolPermissionContext
```

**Flow:** startup computes an ORDERED candidate list (`--dangerously-skip-permissions` → `--permission-mode` → settings defaultMode), skipping bypass when a Statsig gate or settings disable it, skipping `auto` when a SYNC cached-read shows the circuit broken — with a dedicated "no cached value yet" Symbol so cold start defers instead of blocking → the ASYNC check then re-reads config authoritatively, sets the breaker, and returns a TRANSFORM; callers run it inside `setAppState(prev => …)` so mode/prePlanMode/isAutoModeAvailable are re-checked against FRESH context. Kick-out fires only if the user is STILL in auto (or plan-with-auto via prePlanMode/strippedDangerousRules): deactivate classifier flag, restore stashed rules, setMode default, flip availability — notifications decided from the STALE context ("what the user WAS doing"), side effects from the fresh one. Run-once flags reset after /login.

**Invariant:** (1) NEVER return a pre-computed context across an await that gates interactive state — return a closure that re-validates. (2) Notification decisions may use stale data; mutations must not. (3) The sync path must distinguish "gate fetched = disabled" (block now) from "never fetched" (defer to the async check) — conflating them bricks cold start or races it. (4) Entering auto mid-await is possible BEFORE the breaker lands, which is exactly why kick-out re-runs unconditionally for wanted-auto users. (5) canCycleToAuto double-checks cached AND live gate state because they diverge mid-session (getNextPermissionMode.ts :11-16).

**Probe:** coverage caveat — no upstream unit tests reachable. Deterministic pins from repo root: `grep -nF 'can be outrun by a mid-turn shift-tab' src/utils/permissions/permissionSetup.ts` → :1039; `grep -nF "Symbol('no-cached-auto-mode-config')" src/utils/permissions/permissionSetup.ts` → :1335; `grep -nF 'these can' -A1 src/utils/permissions/getNextPermissionMode.ts | head -3` → :12-13 divergence comment; graph search `verifyAutoModeGateAccess` → permissionSetup.ts :1078-1260 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "kickOutOfAutoIfNeeded getAutoModeEnabledStateIfCached transitionPermissionMode", limit: 8 });
```

## Verdict
Adopt transform-based async gate application, the ordered CLI mode ladder with skip-on-disable, the cached-vs-live gate duality, and plan×auto prePlanMode bookkeeping. Adapt gate names/config to your feature-flag service. Omit ant-only `-fast` model-ID heuristics unless you have equivalent internal models.
