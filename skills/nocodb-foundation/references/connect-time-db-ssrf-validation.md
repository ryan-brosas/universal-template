<!-- capsule-v2 -->
# Connect-time DB SSRF validation — how do you close the DNS-TOCTOU window between "host looked safe" and "driver actually connects"?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Where must outbound database-host validation run so a short-TTL DNS flip cannot bypass it, and how do you inject that check into pg vs mysql2 whose socket lifecycles differ?

## Validating stream factory per driver
**Path/Symbol:** `packages/nocodb/src/helpers/dbSsrfLookup.ts:isBlockedIp` (:75–92), `validatingLookup` (:109–132), `pgStreamFactory` (:146–177), `mysql2StreamFactory` (:194–225), `applyDbSsrfProtection` (:249–264); wired at `src/utils/common/NcConnectionMgrv2.ts:172`.
**Signature:** `isBlockedIp(addr: string): boolean`; `validatingLookup: net.LookupFunction`; `pgStreamFactory(): () => net.Socket`; `mysql2StreamFactory(): (opts) => net.Socket`; `applyDbSsrfProtection<T extends {client?, connection?}>(config: T, enabled: boolean): T`.
**Data Shape:** BLOCKED_RANGES = {private, loopback, linkLocal, uniqueLocal, reserved, unspecified, broadcast, carrierGradeNat, teredo, rfc6145}; NAT64 local-use /64:ff9b:1::/48 parsed once at module load; blocked errors carry `code:'EACCES'`.

### Decisive source
```ts
// mysql / mysql2 factory: must return an ALREADY-CONNECTING socket — mysql2 never
// calls `.connect()` on a supplied stream
const socket = net.connect({
  port: cfg.port ?? 3306,
  host: cfg.host,
  lookup: validatingLookup,
});
socket.setNoDelay(true); // replicate mysql2's own socket tuning (skipped for custom streams)
```
(:212–217)

**Flow:** save-time `validateDbConnectionHost` (helpers/validateDbConnectionHost.ts) does fail-fast UX only → the AUTHORITATIVE check rides knex's per-driver `connection.stream` factory installed by `applyDbSsrfProtection(config, isSsrfProtectionEnabled({source: EXTERNAL_DBS}))` at NcConnectionMgrv2.ts:172 (external user-supplied sources only — meta/internal connections return earlier) → pg path: wrap `socket.connect`, translate positional `(port, host)` to options form, validate IP literals directly (`net.isIP` + `isBlockedIp`), else set `opts.lookup = validatingLookup`; mysql2 path: return an ALREADY-connecting socket from `net.connect({...lookup})` because mysql2 never calls `.connect()` on a supplied stream → every resolved address goes through `validatingLookup`, which fails CLOSED if ANY record in a Happy-Eyeballs array is blocked.
**Invariant:** the factory NEVER rewrites `host`, so TLS servername/cert verification stays intact. `isBlockedIp` fails closed on spellings ipaddr.js rejects but Node accepts (`return net.isIP(addr) !== 0`). IPv4-in-IPv6 transition encodings are normalized before range-checking (::ffff: mapped, 2002:: 6to4 bytes 2..5, 64:ff9b::/96 NAT64 bytes 12..15, ::a.b.c.d all-zero-prefix). Unix-socket configs skip DNS entirely (`cfg.socketPath` passthrough). The file MUST stay free of app-internal imports — it is copied VERBATIM into packages/nc-sql-executor; any change here must be mirrored there.
**Probe:** `cd packages/nocodb && grep -c "isBlockedIp" src/helpers/dbSsrfLookup.ts` (=4: def + validatingLookup + 2 IP-literal sites) and `grep -c "process.nextTick" src/helpers/dbSsrfLookup.ts` (=2: refusingSocket destroy + pg literal destroy) and `grep -c "validatingLookup" src/helpers/dbSsrfLookup.ts` (=3: export + 2 factory injections).
**Direct test:** none upstream for this file (109 spec files grepped) — grep probes are the pinned contract.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "applyDbSsrfProtection validatingLookup pgStreamFactory mysql2StreamFactory", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt connect-time validation inside the driver's socket setup + fail-closed multi-record lookup + verbatim-copy discipline; adapt the blocked-range list to your threat model and the injection point to your ORM's config shape; omit the save-time check as anything more than UX (it is not authoritative). Coverage caveat: no direct unit spec; check_index_coverage no_recorded_issue @pin.
