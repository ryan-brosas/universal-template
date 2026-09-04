<!-- capsule-v2 -->
# Fail-closed policy substrate — how do you evaluate an external policy engine inside an approval callback without a throw aborting the run?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** a policy backend (OPA server down, WASM fault, bad path) throws inside the SDK's approval callback — how does the run complete with a structured denial instead of dying?

## evaluatePolicy + opaPolicy — error-as-value substrate and enforce adapter
**Path/Symbol:** `packages/policy-opa/src/opa/evaluate-policy.ts:14` (`export async function evaluatePolicy`, 24L whole); outcome type `EvaluateOutcome` :3–6; consumer `opa/opa-policy.ts:45` (`export function opaPolicy`, deny branch :80–88); degrade variant `optionalOpaPolicy` :132–160; engine-neutral interface `src/policy-client.ts:8` (`PolicyClient`, 20L whole); decision type `src/policy-decision.ts:4` (`PolicyDecision`, 13L whole).

**Signature:**
```ts
type EvaluateOutcome = { ok: true; result: unknown } | { ok: false; error: unknown };
async function evaluatePolicy(client: PolicyClient, path: string, input: unknown): Promise<EvaluateOutcome>;
function opaPolicy<TOOLS, RUNTIME_CONTEXT>(opts: { client: PolicyClient; path: string; toInput?: (args) => unknown }): ToolApprovalConfiguration<TOOLS, RUNTIME_CONTEXT>;
```

**Data Shape:** `PolicyClient` is a one-method interface `evaluate<TInput, TResult>(path, input): Promise<TResult>` so OPA/Cedar/OpenFGA/HTTP-rule engines swap without call-site changes. `PolicyDecision` narrows the SDK's string-or-object `ToolApprovalStatus` to `{type:'approved'|'denied'|'user-approval'|'not-applicable', reason?}` — one discriminant for all downstream code. Default OPA input: `{tool:{name}, args, messages, runtimeContext}`; a custom `toInput` replaces it wholesale.

### Decisive source
```ts
// evaluate-policy.ts — the package's fail-closed invariant in one place
try { return { ok: true, result: await client.evaluate(path, input) }; }
catch (error) { return { ok: false, error }; }

// opa-policy.ts — each caller turns ok:false into its own safe fallback
const outcome = await evaluatePolicy(client, path, opaInput);
if (!outcome.ok) {
  return { type: 'denied', reason: `policy evaluation failed: ${errorMessage(outcome.error)}` };
}
return normalizeOpaDecision(outcome.result);
```

**Flow:** tool call → `toInput` or default input shape → `evaluatePolicy` captures any backend throw as a value → `ok:false` becomes `{type:'denied', reason:'policy evaluation failed: <message>'}` (the model sees a structured result it can reason about, rather than the error rejecting out of the callback and aborting the run) → `ok:true` normalizes the Rego output. `errorMessage` degrades Error→`.message`, object→`JSON.stringify` inside try/catch (circular-safe), else `String(cause)`.

**Invariant:** a thrown `client.evaluate` must NEVER escape into an SDK callback or middleware — the deny-with-reason fallback is computed from the captured error, and the reason names the failure without leaking credential material. `optionalOpaPolicy` extends the same posture to configuration: `client == null` returns `undefined` (SDK falls back to its default allow-all) so a per-environment policy file can be absent in local dev without a code branch at the call site.

**Probe:** `packages/policy-opa/src/opa/opa-policy.test.ts` (9 cases): default input shape asserted with `toHaveBeenCalledWith('p', {tool:{name:'git'}, args, messages, runtimeContext})` (:80–107); custom `toInput` (:109–141); fail-closed deny on throw with reason containing 'OPA unreachable' (:143–168); non-Error throw `{code:'ERR_TIMEOUT'}` serialized into the reason (:170–196); `optionalOpaPolicy` undefined-when-no-client (:199–205). Integration: `opa/opa-policy.integration.test.ts` (4 cases) drives the FULL generateText path with MockLanguageModelV3 — allow executes, deny skips execution and surfaces `execution-denied` with the Rego reason in the tool message (:88–143), a `toInput` dispatcher routes `{kind, args}` through the same rule (:145–231), backend error completes generation with the tool denied (:233–266).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "evaluatePolicy EvaluateOutcome opaPolicy fail closed denied", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: evaluate-policy.ts `evaluatePolicy` :14, opa-policy.ts `opaPolicy` :45, then tests.

## Verdict
Adopt the error-as-value substrate for ANY external dependency called from a framework callback (approval, transform, telemetry hooks); adapt the fallback decision to your posture (deny is correct for security policy; a read-only lookup might degrade to allow); omit the Rego-specific normalization if your engine speaks a different wire shape. Coverage caveat: none — unit-pinned (9 cases) plus a full-path integration suite (4 cases).
