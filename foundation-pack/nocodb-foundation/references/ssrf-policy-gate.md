<!-- capsule-v2 -->
# SSRF policy gate — where does the single "is outbound filtering on?" decision live, and why must env bypasses be per-source?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How do you let self-hosters reach localhost databases/webhooks without handing cloud tenants an SSRF bypass?

## Source-keyed enable ladder
**Path/Symbol:** `packages/nocodb/src/utils/ssrf.ts:isSsrfProtectionEnabled` (:18–50), `getFilteredAgents` (:56–65).
**Signature:** `isSsrfProtectionEnabled({source?: OperationSource}): boolean`; `getFilteredAgents({url, source?}): FilteredAgents` (returns `{}` when disabled).
**Data Shape:** sources = HOOKS / EXTERNAL_DBS / DATA_IMPORT from nocodb-sdk OperationSource; agents from request-filtering-agent's `useAgent(url)`.

### Decisive source
```ts
// Cloud always enforces SSRF protection — env bypasses are ignored
if (isCloud) return true;
// Global override — disables all SSRF protection for self-hosted
if (process.env.NC_DISABLE_SSRF_PROTECTION === 'true') return false;
if (source === OperationSource.HOOKS &&
    (process.env.NC_ALLOW_LOCAL_HOOKS === 'true' ||
     process.env.NC_WEBHOOK_ALLOW_PRIVATE_NETWORK === 'true')) return false;
```
(:23–:35)

**Flow:** isCloud → unconditional enforce (a tenant must never opt out of protecting shared hosts) → global kill-switch → per-source env bypasses (`NC_ALLOW_LOCAL_HOOKS`/`NC_WEBHOOK_ALLOW_PRIVATE_NETWORK`, `NC_ALLOW_LOCAL_EXTERNAL_DBS`, `NC_ALLOW_LOCAL_DATA_IMPORT`) → default ON. Consumers call this ONE function before every outbound surface: DB connections (NcConnectionMgrv2 → applyDbSsrfProtection), webhook HTTP (utils.service), attachment URL fetches (attachments.service via getFilteredAgents), storage plugins (S3/GCS/Minio/Slack/Discord/Teams/Mattermost all take getFilteredAgents).
**Invariant:** the decision is keyed by SOURCE, not by caller — one env var cannot silently open every egress class. When disabled, `getFilteredAgents` returns `{}` so call sites can spread it without conditional plumbing. The DB host check (validateDbConnectionHost) and this gate share `isBlockedIp` semantics so save-time and connect-time agree.
**Probe:** `cd packages/nocodb && grep -c "NC_ALLOW_LOCAL" src/utils/ssrf.ts` (=3) and `grep -c "isCloud" src/utils/ssrf.ts` (=2: import + check).
**Direct test:** none upstream for utils/ssrf.ts — grep probes pin the ladder.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "isSsrfProtectionEnabled getFilteredAgents OperationSource useAgent", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the source-keyed policy function + cloud-always-enforce ordering; adapt env names to your config convention; omit request-filtering-agent if you have your own IP-filtering agent. Coverage caveat: grep-pinned only; coverage clean @pin.
