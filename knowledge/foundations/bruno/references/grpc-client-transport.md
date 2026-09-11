# gRPC client transport ladder — Bruno's grpc-client.js contracts

**Source:** bruno (MIT), `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno` ready (27,553n/96,755e). **Question:** When porting a gRPC-capable request tool, what URL, TLS, proxy, reflection, and stream-lifecycle contracts must hold?

**Path/Symbol:** `packages/bruno-requests/src/grpc/grpc-client.js` (1,077L) `GrpcClient`, `grpcMessageGenerator.js`, `grpc-client.spec.js` (718L direct tests, present at pin).

## URL grammar ladder (`getParsedGrpcUrlObject`)
- TCP: no scheme + localhost/127.0.0.1 → `grpc://`, else default `grpcs://` (secure!), then `new URL()`.
- Unix socket: `unix:` / `unix:///` / `unix-abstract:` → `isLocalTransport`, host kept raw.
- Windows pipe: `\\.\\pipe\\` or `//./pipe/` → normalized `//./pipe/` → `\\.\\pipe\\`; `isLocalTransport`.
- Trailing slash stripped from path; `requestPath = path + rpcMethod` (e.g. `/package.Service/Method`).

## Precision + proto grammar (`configOptions`)

## Credentials ladder (`#getChannelCredentials`)
Local transport (unix/pipe) → `ChannelCredentials.createInsecure()`. Protocol not in {`grpcs`,`https`} → insecure. Else SSL: no pfx/passphrase → `createSsl(ca, key, cert, sslOptions)`; pfx/passphrase → `tls.createSecureContext` then `createFromSecureContext`. `rejectUnauthorized: verifyOptions?.rejectUnauthorized !== false` (defaults TRUE — fail-closed). Any credential-building error → falls back to insecure (loud log).

## Proxy ladder (`#resolveProxyTarget`)
- proxyConfig undefined/null → leave env var proxy behavior untouched.
- proxyConfig object (even with null URL) → `grpc.enable_http_proxy: 0` + `grpc.use_local_subchannel_pool: 1` (Bruno owns proxy; env vars must not interfere).
- Local transports skip proxying. Otherwise manual HTTP CONNECT replication: target = proxy host:port, `grpc.http_connect_target: dns:<original>`, `grpc.default_authority: <original>`, `grpc.http_connect_creds` = decoded usernpass. SOCKS/HTTPS proxies unsupported.

## Stream dispatch & lifecycle
`#getMethodType` from streaming flags → unary/client/server/bidi. `#addConnection` cancels + closes existing same-id (leak prevention). `#removeConnection` closes channel on completion. `end()` signals EOF only — does NOT close channel because response stream may stay active.

## Event latch
`setupGrpcEventHandlers` — single-shot `complete()` latch: status / error / end / cancel emit AND complete; data and metadata events do not complete so long-lived streams keep reporting. Each terminal event carries metadata with Buffer→base64 normalization.

## Sample-message generation
`generateGrpcSampleMessage` walks request fields; TYPE_MESSAGE recurses, repeated → arrays (arraySize/faker 1-3), ints via faker int, bytes → base64, enums → 0. No field info → `{}`.

## Verdict
Adopt the URL ladder, insecure-for-local defaulting, fail-closed rejectUnauthorized, manual HTTP CONNECT replication, single-fire event latch, and close-on-complete channel discipline. Direct tests `grpc-client.spec.js` (718L) exist at pin; not executed here (no workspace deps) — recorded as a caveat, not fabricated green.
