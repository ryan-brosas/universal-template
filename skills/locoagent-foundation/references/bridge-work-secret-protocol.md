<!-- capsule-v2 -->
# Bridge work-secret envelope — how does a polled work item authorize a session?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How is the server-minted work payload decoded into credentials, and which URL/auth shape does each protocol version need?

## Path/Symbol
**Path/Symbol:** `src/bridge/workSecret.ts` — `decodeWorkSecret` (:6-32), `buildSdkUrl` (:41-48), `sameSessionId` (:62-73), `buildCCRv2SdkUrl` (:81-87), `registerWorker` (:97-127); `src/bridge/types.ts` — `WorkSecret` (:33-51), `WorkResponse.secret` ("base64url-encoded JSON", :29).
**Signature:** `decodeWorkSecret(secret: string): WorkSecret` throws on version≠1 or missing `session_ingress_token`/`api_base_url`; `registerWorker(sessionUrl, accessToken): Promise<number>` (worker_epoch); `sameSessionId(a,b): boolean`.
**Data Shape:** `WorkSecret = {version:1, session_ingress_token, api_base_url, sources[], auth[], claude_code_args?, mcp_config?, environment_variables?, use_code_sessions?}` — `use_code_sessions` is the SERVER-driven v2 selector (`prepare_work_secret()` sets it when `ccr_v2_compat_enabled`).

### Decisive source
```ts
export function decodeWorkSecret(secret: string): WorkSecret {
  const json = Buffer.from(secret, 'base64url').toString('utf-8')
  const parsed: unknown = jsonParse(json)
  if (!parsed || typeof parsed !== 'object' || !('version' in parsed) ||
      parsed.version !== 1) {
    throw new Error(`Unsupported work secret version: ...`)
  }
  ...
}
// protojson serializes int64 as a string to avoid JS number precision loss;
// the Go side may also return a number depending on encoder settings.
const raw = response.data?.worker_epoch
const epoch = typeof raw === 'string' ? Number(raw) : raw
```

**Flow:** work poll returns `{id, data:{type,id}, secret}` → base64url-decode → strict-validate (version===1, non-empty ingress token) → the JWT inside doubles as the **ack credential** (`acknowledgeWork(envId, work.id, secret.session_ingress_token)`) AND the child's access token. Version branch: `use_code_sessions===true` → `buildCCRv2SdkUrl` (HTTP(S) `/v1/code/sessions/{id}`, child derives SSE+worker paths) after `registerWorker` mints an epoch; else `buildSdkUrl` → ws(s)://host/**v2**/session_ingress/ws/{id} for localhost (direct, no Envoy) but **/v1/** for production (Envoy rewrite).

**Invariant:** (1) A porter who treats `worker_epoch` as a JSON number breaks on protojson string encoding — accept both, require `Number.isSafeInteger`. (2) The ws URL version segment is environment-dependent (localhost=v2 direct, prod=v1 rewritten) — hardcoding either silently kills one deployment. (3) Decode failure means you cannot ack (ack needs the JWT you failed to decode); callers must `stopWork` (OAuth-authed) to poison-pill the item out of Redis XAUTOCLAIM redelivery. (4) `version!==1` throws rather than best-effort parsing — forward-compat is deny-by-default.

**Probe:** coverage caveat — no upstream unit tests for this file. Deterministic pins: `grep -n "Unsupported work secret version" src/bridge/workSecret.ts` (:16); `grep -n "protojson serializes int64" src/bridge/workSecret.ts` (:113); `grep -n "isLocalhost ? 'v2' : 'v1'" src/bridge/workSecret.ts` (:45); graph resolves `locoagent.src.bridge.workSecret.decodeWorkSecret` :6-32 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "decodeWorkSecret registerWorker buildSdkUrl buildCCRv2SdkUrl worker_epoch", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole: the base64url envelope with version-gated strict validation and the dual-role ingress JWT are exactly reusable for any poll-dispatch job system. Adapt the localhost/prod URL split to your gateway topology; omit the GitHub source fields if your dispatcher carries none.
