<!-- capsule-v2 -->
# Runtime + config plumbing — auth acceptance mirroring, namespaced settings merge, and the observation-channel scrub erratum

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** How should an auxiliary LLM consumer reuse the host session's model/auth, and how do layered configs merge safely? *(Auth half narrowed at pass 3 [DONE:347]: the full empty-payload decision ladder now lives in request-time-signing-gate.md / stale-snapshot-recheck.md / valueless-diagnostics.md.)*

## Model resolution with OAuth-aware auth check (`src/runtime.ts`)
**Path/Symbol:** `runtime.ts:20-23` (`hasUsableAuth`), `runtime.ts:126-220` (`Runtime.resolveModel`; returns `env`/`baseUrl` too since ce9fc982).
**Signature:** `resolveModel(ctx: {model, modelRegistry, hasUI, ui}): Promise<ResolveResult>` — `{ok:true, model, apiKey?, headers?, env?, baseUrl?}` | `{ok:false, reason}`.
**Data Shape:** configured override = `{provider, id, thinking?}` looked up in the host's registry; falls back to the SESSION model with a warning when not found.

### Decisive source
```ts
/**
 * Mirrors pi's own request-auth acceptance rule (`AgentSession._getRequiredRequestAuth`):
 * resolved auth is usable when it carries an apiKey OR at least one header value.
 * OAuth providers ... authenticate via `toAuth()` returning
 * { headers: { Authorization: "Bearer …" } } with no apiKey.
 */
function hasUsableAuth(auth: { apiKey?: unknown; headers?: unknown }): boolean {
	if (typeof auth.apiKey === "string" && auth.apiKey.length > 0) return true;
	return countUsableHeaders(auth.headers) > 0;
}
```

**Flow:** configured model wins if found (else warn + fall back to session model) → fetch apiKey+headers+env+baseUrl → accept EITHER a non-empty apiKey OR any non-empty header value → failure reasons distinguish expired-OAuth from missing-key so users get the right fix. What happens when BOTH are absent is a THREE-state decision (ambient signing vs expired OAuth vs misconfiguration) — owned by request-time-signing-gate.md; this capsule pins only the usable-auth predicate itself.
**Invariant:** Treating "no apiKey" as "no auth" breaks every OAuth provider — headers-only auth is first-class. The mirror-the-host-rule comment is part of the contract: if your host changes its acceptance rule, this predicate must follow.

## Namespaced config merge (`src/config.ts`)
**Path/Symbol:** `config.ts:131-252` (`loadConfig`, `readNamespacedConfig`, `readEnvConfig`, validators).
**Signature:** `loadConfig(cwd, env): Config` — global `<agentDir>/settings.json` → project `<cwd>/.pi/settings.json` → env, all under the `"observational-memory"` namespace key.
**Data Shape:** derived field: `observationsPoolTargetTokens` defaults to floor(max/2); a target ≥ max or ≤ 0 is DISCARDED (falls back to derived).

### Decisive source
```ts
const merged = {
	...DEFAULTS,
	observationsPoolTargetTokens: undefined,   // never inherit DEFAULT target; derive unless set
	...globalConfig, ...projectConfig, ...envConfig,
};
const target = validTargetOrUndefined(merged.observationsPoolTargetTokens, merged.observationsPoolMaxTokens)
	?? derivedObservationPoolTarget(merged.observationsPoolMaxTokens);
```
```ts
export function readEnvConfig(env): Partial<Config> {
	const rawPassive = env["PI_OBSERVATIONAL_MEMORY_PASSIVE"];
	...if (["1","true","yes","on"].includes(passive)) return { passive: true }; ...
}
```

**Flow:** read each layer defensively (missing file / bad JSON ⇒ empty partial; every field re-validated by type — positive ints, ratio strictly in (0,1), enum membership) → merge → post-merge DERIVATION for the dependent field (target must be < max).
**Invariant:** Cross-field invariants are enforced AFTER merge, not per-layer — a valid-per-layer but globally-invalid combo still degrades safely. The pre-set `undefined` prevents DEFAULTS' concrete target from defeating user max overrides. Env vars handle only boolean kill-switches (`passive`), parsed permissively.

## ERRATUM (pass 3) — the old "RED FLAG: scrubbed source" claim was WRONG
**Path/Symbol:** prior revision cited `runtime.ts:88` + `consolidation-trigger.ts:312,384,456` as containing literal `***` scrub artifacts that "do not typecheck".
### Verified reality (byte census at ce9fc982)
```bash
python3 - <<'EOF'
import pathlib
for f in ['src/runtime.ts','src/hooks/consolidation-trigger.ts']:
    b=pathlib.Path(f).read_bytes()
    print(f, 'triple-star:', b.count(b'***'),
          '| typeof-auth-apiKey:', b.count(b'typeof auth.apiKey'),
          '| apiKey-as-string:', b.count(b'apiKey as string | undefined'))
EOF
# src/runtime.ts triple-star: 0 | typeof-auth-apiKey: 2 | apiKey-as-string: 1
# src/hooks/consolidation-trigger.ts triple-star: 0
```
The repo NEVER contained `***`: real expressions (`typeof auth.apiKey === "string" && …`, `auth.apiKey as string | undefined`) are intact and the tree typechecks. The `***` appears ONLY in an LLM agent's content-printing observation channel — a credential-flow sanitizer rewrites those expressions when source text is displayed to the model. A prior lane mistook its own tool output for repo state.
**Invariant:** When a quote shows an impossible expression, verify with BYTE counts (`python3 pathlib.read_bytes().count()`, or grep -cF piped through wc — anything EXCEPT pasting the file into your context) before concluding the source is broken; and never trust your own transcript rendering of credential-adjacent code. Port credential flow from types/call sites regardless.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "hasUsableAuth resolveModel loadConfig normalizeSettingsConfig readEnvConfig resolveCompactAfterTokens", limit: 10 });
```
(Direct tests: `tests/runtime.test.ts` pins auth acceptance/failure paths; `tests/config.test.ts` pins merge/validation/derivation.)

## Verdict
Adopt the apiKey-OR-headers auth predicate, OAuth-specific failure guidance, three-layer namespaced config merge with per-field validation and post-merge cross-field derivation, and env-only kill switches. Adapt settings paths and env names. Omit nothing behavioral — but treat every impossible-looking expression in YOUR OWN reading channel as a suspect sanitization artifact first: verify bytes before believing.
