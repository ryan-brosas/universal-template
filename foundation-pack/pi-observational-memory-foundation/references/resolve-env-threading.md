<!-- capsule-v2 -->
# Resolve-env threading — which resolved-auth fields must reach every worker LLM call, and what fails silently when one is dropped

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When an auxiliary LLM consumer resolves credentials once via the host registry, which fields must be forwarded END-TO-END into every worker call — and what silently 404s if you drop one?

## Path/Symbol
**Path:** `src/runtime.ts`, `src/hooks/consolidation-trigger.ts`, `src/agents/{observer,reflector,dropper}/agent.ts`.
**Symbol:** `ResolveResult` **runtime.ts:3-5** (gained `env?`/`baseUrl?`), `Runtime.resolveModel` returns them at **runtime.ts:217-218**; stage forwards `env: resolved.env` at **consolidation-trigger.ts:314** (observer), **:387** (reflector), **:460** (dropper); worker arg interfaces + destructures at `observer/agent.ts:18/:103`, `reflector/agent.ts:26/:109`, `dropper/agent.ts:44/:135`.

**Signature:** `{ ok: true; model: unknown; apiKey?: string; headers?: Record<string,string>; env?: Record<string,string>; baseUrl?: string } | { ok: false; reason: string }`.

**Data Shape:** the host facade's resolution may carry `env` (extra process-env entries the provider needs, e.g. `CLOUDFLARE_ACCOUNT_ID`) and `baseUrl` (possibly a TEMPLATE containing `{ENV_VAR}` placeholders, e.g. `https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1`). Substitution happens where requests are built — so a dropped `env` leaves the literal `{CLOUDFLARE_ACCOUNT_ID}` in the URL and every call 404s.

### Decisive source
```ts
// runtime.ts — the result must carry everything the host handed over
return {
    ok: true,
    model,
    apiKey: auth.apiKey as string | undefined,
    headers: auth.headers as Record<string, string> | undefined,
    env: auth.env as Record<string, string> | undefined,
    baseUrl: auth.baseUrl as string | undefined,
};
```
```ts
// consolidation-trigger.ts:310-315 — EVERY stage forwards all four fields
const observations = await runObserver({
    model: resolved.model as any,
    apiKey: resolved.apiKey,
    headers: resolved.headers,
    env: resolved.env,          // ← the field whose absence caused the outage
    ...
```

**Flow:** `makeModelResolver` caches ONE resolution per consolidation run → each stage (`runObserverStage` :257, `runReflectorStage` :379, `runDropperStage` :452) calls it → forwards `model`+`apiKey`+`headers`+`env` into its worker's args → worker passes them verbatim into its `streamSimple` LLM call. `baseUrl` rides on `ResolveResult` but today has NO internal consumer (grep `.baseUrl` src/ → only runtime.ts:218): it is carried for boundary parity with the host's request config.

**Invariant (the porter trap):** A credential bundle is not just "key or header" — providers exist (cloudflare-workers-ai with full `@cf/...` ids) whose entire usability hangs on `env` reaching the request layer. Before commit 6f694e6, `resolveModel` dropped `auth.env`/`auth.baseUrl`; observational memory produced 404s against Cloudflare and NOTHING ELSE looked wrong (auth had succeeded). Rule: your resolved-credential type must mirror the host's resolution shape FIELD FOR FIELD, and every stage must forward ALL fields even ones it does not understand. Asymmetry note for auditors: `env` is load-bearing (threaded into all three workers); `baseUrl` is currently pass-through surface — keep both when porting.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
grep -c "env: resolved.env" src/hooks/consolidation-trigger.ts   # expect 3 && \
grep -n "forwards env and baseUrl" tests/runtime.test.ts         # line 163 && \
npx vitest run tests/runtime.test.ts                             # 11 passed (incl. the toEqual full-shape pin)
```

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "ResolveResult resolveModel env baseUrl runObserverStage", limit: 5 });
// rank1 resolves Runtime.resolveModel Method src/runtime.ts 126-220
```

**Verdict:** Adopt field-complete credential forwarding: resolve once per run, forward model/apiKey/headers/env into EVERY worker call, keep baseUrl on the result type. Adapt field names to your host's resolution surface. Omit nothing — the test pins the FULL result object with toEqual, so any dropped field fails loudly there.
