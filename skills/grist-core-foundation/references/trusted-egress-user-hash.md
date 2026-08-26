<!-- capsule-v2 -->
# Trusted egress & salted user hash — how do assistant API calls honor the proxy policy, and how is the user identified upstream?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Which proxy agent carries LLM traffic, and what pseudonymous identifier goes in the request body?

## DEPS.agents.trusted attaches only when configured; getUserHash = sha256(id + ref + hardcoded salt), logged for support correlation
**Path/Symbol:** `app/server/lib/OpenAIAssistantV1.ts`: `DEPS = { fetch, delayTime: 1000, agents }` (:34, test seam), trusted-agent spread (:213); `app/server/lib/Assistant.ts`: `getUserHash` (:91–105) — salt :94, log-with-hash :99–103.
**Signature:** `getUserHash(session: OptDocSession): string` (base64 sha256).
**Data Shape:** Request body: `{messages, temperature: 0, model?, user, max_tokens?}` — user is the HASH, not an id.

### Decisive source
```ts
export const DEPS = { fetch, delayTime: 1000, agents };   // mocked/replaced in tests
...
...(DEPS.agents.trusted ? { agent: DEPS.agents.trusted } : {}),
...
const salt = "7a8sb6987asdb678asd687sad6boas7f8b6aso7fd";
const hashSource = `${user?.id} ${user?.ref} ${salt}`;
const hash = createHash("sha256").update(hashSource).digest("base64");
// So that if we get feedback about a user ID hash, we can
// search for the hash in the logs to find the original user ID.
log.rawInfo("getUserHash", { ...getLogMeta(session), userRef: user?.ref, hash });
```

**Flow:** every completion POST rides `DEPS.agents.trusted` (GristProxyAgent from ProxyAgent.ts) when configured — untrusted hosts otherwise default-agent. temperature pinned to 0 for reproducible formula help; `user` field carries the salted hash so OpenAI-side abuse signals can't be joined to real identities from outside, while OUR logs record hash+ref together making support reverse-lookup possible internally.
**Invariant:** The salt is hardcoded NOT secret (it's in the repo): its job is defeating trivial rainbow/id-guessing, not hashing security — a porter "improving" it to a server secret breaks log correlation. DEPS indirection exists so tests swap fetch/delay without module hacks (`test/server/lib/OpenAIAssistantV1.ts` stubs exactly these). Omitting the agent option when unset (spread of undefined key) matters: node-fetch must not receive agent:undefined semantics differences.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "DEPS.agents.trusted" app/server/lib/OpenAIAssistantV1.ts && grep -n "temperature: 0" app/server/lib/OpenAIAssistantV1.ts && sed -n "147,158p" test/server/lib/OpenAIAssistantV1.ts | grep -c "proxy"'` → :213, :204, proxy tests present.
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` :147 "does not use the trusted proxy when not configured", :159 "uses trusted proxy when configured".

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getUserHash agents trusted ProxyAgent fetch","limit":5,"detail":"ids"}'
```

## Verdict
Adopt DEPS-injection seam + conditional agent attachment + hash-not-id upstream identity; adapt salt/log fields; omit the hash entirely only if your provider contract forbids user fields.
