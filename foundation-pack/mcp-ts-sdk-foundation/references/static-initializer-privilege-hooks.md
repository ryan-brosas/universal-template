<!-- capsule-v2 -->
# Static-initializer privilege hooks — how do package-internal serving entries write private state without making it public API?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do sibling modules (HTTP/stdio entries) install handlers and stamp identity on a `Server` instance whose fields are private — without widening the public surface?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: module-level hook vars (:207-209), `static {}` block binding closures (:265-284), exported wrappers `seedClientIdentityFromEnvelope` (:226-228), `installModernOnlyHandlers` (:239-241), `serverIdentityOf` (:250-252).
**Signature:** `let writeClientIdentity: (server: Server, identity: PerRequestClientIdentity) => void;` etc. — assigned once in the class static block.
**Data Shape:** Three closures over private members: `_clientCapabilities`/`_clientVersion`, `_supportedProtocolVersions` + `setRequestHandler`, `_serverInfo`.

### Decisive source
```ts
let writeClientIdentity: (server: Server, identity: PerRequestClientIdentity) => void;
let installDiscoverHandler: (server: Server, servedModernVersions: readonly string[]) => void;
let readServerIdentity: (server: Server) => Implementation;

export class Server extends Protocol<ServerContext> {
    static {
        writeClientIdentity = (server, identity) => { /* writes privates */ };
        installDiscoverHandler = (server, servedModernVersions) => {
            const missing = servedModernVersions.filter(v => !server._supportedProtocolVersions.includes(v));
            if (missing.length > 0) {
                // Never mutate the existing array in place: the default supported-versions
                // list is a shared module constant.
                server._supportedProtocolVersions = [...server._supportedProtocolVersions, ...missing];
            }
            server.setRequestHandler('server/discover', () => server._ondiscover());
        };
        readServerIdentity = server => server._serverInfo;
    }
```

**Flow:** entry (createMcpHandler/serveStdio) imports the thin wrappers → wrappers invoke the static-block closures → closures touch genuinely private state → instances built by consumers never see these paths and keep answering `-32601` for `server/discover` unless their own supported-versions list opts into a modern revision. Idempotent by construction (filter before append; handler re-set harmless).

**Invariant:** The exported wrapper names are deliberately NOT re-exported from the package index — package-internal capability, not public API. Copy-with-spread instead of in-place mutation protects the shared default constant from cross-instance corruption.

**Probe:** `packages/server/test/server/discover.test.ts` (modern-only handler installation + advertisement); `invokeSeam.test.ts` :98 ("protects unmarked instances: modern-classified traffic gets the protocol-version error" — hand-built instance stays era-gated); `protocolExport.test.ts` (public-surface pinning).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "installModernOnlyHandlers seedClientIdentityFromEnvelope writeClientIdentity", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt static-block privilege closures for cross-module private access when you cannot/won't use `friend` semantics or `#`-symbol keyed registries; adapt to your language (TS module scope ≈ package-private); omit the specific MCP handlers.
