<!-- capsule-v2 -->
# Embedded d.ts stub plane — how does a non-JS product give its scripting layer full IntelliSense?

**Source:** JetBrains IDE distributions (proprietary distribution; study/reference use only); direct jar reads; Codebase Memory `jetbrains-clion`. **Question:** How do IDEs whose embedded scripts run inside a host object (no npm, no node) ship type information for that host?

## Host-object stubs as data
**Path/Symbol:** `plugins/restClient/lib/restClient.jar!com/intellij/ws/rest/client/stubs/http-client*.d.ts` (5 files).
**Signature:** ambient declarations only: `declare const response: HttpResponse;` + `interface HttpClient { test(name: string, func: Function): void; assert(condition: boolean, message?: string): void; exit(): void; }`.
**Data Shape:** cluster census 338 `.d.ts` across 13 products. Two populations: (a) genuine API stubs like restClient's 5-file set (`http-client.d.ts`, `-crypto`, `-common`, `-dynamic-variables`, `-pre-request` — one per script context/sandbox), header comment states intent verbatim: "It doesn't perform any real operation and should be used for documentation purpose"; (b) webjars-bundled third-party libs inside web-preview plugins (swagger's react-component jar = 48 d.ts of its own React code). Population (a) is the pattern; (b) is cargo.

### Decisive source
```typescript
/**
 * The file provides stubs for JavaScript objects accessible from HTTP Client
 * response handler scripts.
 * It doesn't perform any real operation and should be used for documentation purpose.
 */
declare const response: HttpResponse;

interface HttpClient {
    test(testName: string, func: Function): void;
    assert(condition: boolean, message?: string): void;
    exit(): void;
}
```

**Flow:** user writes a response-handler script → JS analysis resolves `response`/`client` from the ambient d.ts (attached by the plugin's registration, not by any import) → completion/signature-help/docs render from the stub JSDoc → at runtime the host injects the REAL objects, which may implement more than the stub declares.
**Invariant:** stubs are deliberately lie-by-omission documentation of the sandbox surface — they must NEVER be executed or bundled into shipped JS; each script CONTEXT gets its own stub file because available globals differ per hook (`pre-request` sees different globals than response handlers). Wrong port: importing the stub as a module.
**Probe:** `unzip -p clion/plugins/restClient/lib/restClient.jar com/intellij/ws/rest/client/stubs/http-client.d.ts | head -5` → documentation-purpose header; census loop counting `.d.ts` in plugins/*/lib/*.jar reproduces 338 cluster-wide.
**Coverage caveat:** resource-plane capsule; cited via direct jar extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "rest client http client script response handler", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: ship ambient .d.ts per execution-context to document host-injected script surfaces; keep runtime truth in host code, types in data. Adapt to your host's scripting embeds. Omit webjars-cargo population (b) from any count-based reasoning. Sibling pattern to php-stubs-plane (pass 3): same trick, PHP empty-body stubs vs TS ambient declarations.
