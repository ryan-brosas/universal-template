<!-- capsule-v2 -->
# Lazy peer-dependency policy clients — how do you bind an optional policy backend without making it a hard dependency or swallowing a broken bundle?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** the policy engine SDKs are optional peer dependencies — how do the two clients defer the import, fail with an actionable error, and still refuse a mis-built WASM bundle?

## httpPolicyClient + wasmPolicyClient — lazy-import backends with fail-closed evaluation
**Path/Symbol:** `packages/policy-opa/src/opa/http-policy-client.ts:17` (`export function httpPolicyClient`, 57L whole; lazy import :34–50); `packages/policy-opa/src/opa/wasm-policy-client.ts:28` (`export async function wasmPolicyClient`, 78L whole; import :40–46, setData :52–54, evaluate :57–77).

**Signature:**
```ts
function httpPolicyClient(opts: { url: string; headers?: Record<string, string> }): PolicyClient;
async function wasmPolicyClient(opts: { wasm: Uint8Array | ArrayBuffer; data?: unknown }): Promise<PolicyClient>;
```

**Data Shape:** both return the one-method `PolicyClient`. HTTP: `url` typically `http://localhost:8181`, `headers` forwarded for Styra DAS / EOPA auth. WASM: bundle compiled offline with `opa build -t wasm`; optional `data` document passed to `setData`; the `path` argument to `evaluate` is INFORMATIONAL for WASM (the entrypoint is fixed at build time) — recorded for audit logs only.

### Decisive source
```ts
// http-policy-client.ts — constructor never throws; first evaluate does
let underlying: Underlying | undefined;
async function getUnderlying(): Promise<Underlying> {
  if (underlying) return underlying;
  let mod: OPAModule;
  try { mod = await import('@open-policy-agent/opa'); }
  catch (cause) {
    throw Object.assign(new Error('Cannot import "@open-policy-agent/opa". Install it as a peer dependency to use httpPolicyClient().'), { cause });
  }
  underlying = new mod.OPAClient(url, headers ? { headers } : undefined);
  return underlying;
}

// wasm-policy-client.ts — refuse a bundle that produced nothing
const results = policy.evaluate(input);
if (!Array.isArray(results) || results.length === 0) {
  throw Object.assign(new Error('OPA WASM policy produced no result. Check that the bundle was built with the correct entrypoint (`opa build -t wasm -e <path>`).'), { input });
}
return results[0].result as never;
```

**Flow:** HTTP — construction is pure (test asserts the factory does not throw without the peer dep installed); the dynamic import happens on FIRST `evaluate`, is memoized into `underlying`, and a missing module throws an install-instruction error with the underlying import failure attached as `cause`. WASM — `loadPolicy` at construction (async factory), optional `setData` only when the loaded policy exposes it, then per-evaluate: array-of-`{result}` entries → first entry's `result`; empty or non-array ⇒ throw naming the `opa build -e` fix.

**Invariant:** two distinct failure postures by design — a MISSING peer dependency is an actionable setup error (message names the package and the fix, `cause` preserved ES2018-safe), while a MIS-BUILT bundle is an evaluation error thrown (not a silent `undefined`) so the fail-closed substrate above reads it as deny, never as "no opinion". A legitimately falsy result (`{result: false}`) is preserved — the guard is on array shape/emptiness, never on truthiness.

**Probe:** `packages/policy-opa/src/opa/http-policy-client.test.ts` (3 cases): install-as-peer-dep error regex, `cause` defined, constructor does not throw. `opa/wasm-policy-client.test.ts` (2 cases): same error/cause pair for opa-wasm. `opa/wasm-policy-client.evaluate.test.ts` (4 cases, mocked loadPolicy): first-entry result returned; empty array throws /produced no result/; `{result: false}` resolves `false`; non-array (null) throws the same named error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "httpPolicyClient wasmPolicyClient loadPolicy peer dependency lazy import", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: http-policy-client.ts :17, wasm-policy-client.ts :28, then their tests.

## Verdict
Adopt lazy-import + actionable-error + cause-preservation for any optional heavy dependency; adapt the memoization (HTTP) and build-time entrypoint contract (WASM) to your engine; omit the setData path if your bundles carry no data documents. Coverage caveat: none — all three suites test-pinned (9 cases total); the real HTTP/WASM round-trip is covered upstream only by the integration suite pattern, not in unit runs.
