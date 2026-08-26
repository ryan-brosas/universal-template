<!-- capsule-v2 -->
# SSL file-path timing oracle — how do you offer server-side cert-file reads to self-hosters without leaking file existence to tenants?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What three defenses stack against the `ssl.{ca,key,cert}FilePath` file-existence oracle, and in what order?

## Reject-then-pad defense stack
**Path/Symbol:** `packages/nocodb/src/helpers/validateDbConnectionHost.ts:validateDbConnectionSslPaths` (:40–50), `hasSslFilePath` (:20–24); `packages/nocodb/src/helpers/withMinResponseTime.ts:withMinResponseTime` (:19–33), `SSL_FILE_PATH_TEST_MIN_RESPONSE_MS = 1500`.
**Signature:** `validateDbConnectionSslPaths(ssl: unknown): void` (throws NcError.badRequest); `hasSslFilePath(ssl): boolean`; `withMinResponseTime<T>(minMs: number, fn: () => Promise<T>): Promise<T>`.
**Data Shape:** SSL_FILE_PATH_KEYS = ['caFilePath','keyFilePath','certFilePath']; floor constant 1500ms must exceed the driver's connect-timeout.

### Decisive source
```ts
// Cloud always enforces; env bypass is ignored (a tenant must not be able
// to probe shared-host files).
if (!isCloud && process.env.NC_DISABLE_DB_SSL_FILE_PATHS !== 'true') return;
if (hasSslFilePath(ssl)) {
  NcError.badRequest(
    'SSL certificate file paths are not allowed; provide the certificate contents instead',
  );
}
```
(:43–:49)

**Flow:** (1) GUARD — on Cloud (or self-hosted opt-in `NC_DISABLE_DB_SSL_FILE_PATHS=true`) reject any ssl config carrying a file-path key BEFORE any filesystem access, so a blocked request never touches disk and emits no timing/error signal → (2) PAD — where reads remain allowed (self-host default), wrap the connection-test endpoint in `withMinResponseTime(1500, fn)` whose try/finally pads BOTH success and failure to a common wall-clock floor: missing path fails fast, existing path proceeds into a slower connect, and the sub-floor differential disappears → (3) the floor value must exceed the driver's connect-timeout or an attacker pairing an unreachable host with path probing still observes the connect-timeout tail.
**Invariant:** rejection must precede disk access (defense-in-depth comment names padding as protection for the self-host path ONLY). The pad runs in `finally`, so rejections are padded too. On Cloud the env bypass is deliberately ignored.
**Probe:** `cd packages/nocodb && grep -c "SSL_FILE_PATH_TEST_MIN_RESPONSE_MS" src/helpers/withMinResponseTime.ts` (=1 const decl; consumers import it) and `grep -c "hrtime.bigint" src/helpers/withMinResponseTime.ts` (=2 start+elapsed).
**Direct test:** none upstream for these helpers — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "withMinResponseTime validateDbConnectionSslPaths hasSslFilePath caFilePath", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reject-before-disk + common-floor response padding + floor-exceeds-connect-timeout sizing; adapt the guard's cloud/env split to your tenancy model; omit padding entirely if you never read caller-named server files. Coverage caveat: grep-pinned only.
