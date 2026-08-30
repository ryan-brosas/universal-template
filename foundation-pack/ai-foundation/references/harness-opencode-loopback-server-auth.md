<!-- capsule-v2 -->
# OpenCode loopback server auth — how do you authenticate a loopback dev server you just spawned without a config file or a fixed secret?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** how does the bridge prove to its own just-spawned OpenCode HTTP server that requests are the host, when both sides share only a process env block?

## configureOpenCodeServerAuth
**Path/Symbol:** `packages/harness-opencode/src/bridge/opencode-server-auth.ts` (15L whole); consumption `bridge/index.ts` :185 (`const serverAuthHeaders = configureOpenCodeServerAuth({ env: procEnv })` immediately before `createOpencodeServer`, then the returned header is pinned onto `createOpencodeClient({baseUrl: server.url, directory: workdir, headers: serverAuthHeaders})` :191–198). Companion: `opencode-path.ts` (17L whole) — `prependOpenCodeBinToPath` puts `<bootstrapDir>/node_modules/.bin` at the FRONT of `procEnv.PATH` (with a fixed FHS fallback `/usr/local/sbin:…:/bin` when PATH is empty) so the spawned `opencode` binary resolves to the bootstrap-installed version, wired at bridge/index.ts :128.

### Decisive source
```ts
import { randomBytes } from 'node:crypto';

export function configureOpenCodeServerAuth({
  env,
}: {
  env: Record<string, string | undefined>;
}): { Authorization: string } {
  const username = env.OPENCODE_SERVER_USERNAME ?? 'opencode';
  const password = randomBytes(32).toString('hex');
  env.OPENCODE_SERVER_PASSWORD = password;

  return {
    Authorization: `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`,
  };
}
```

**Data Shape:** one call does three things atomically: reads an optional username from env (default `'opencode'`), generates a fresh 256-bit hex password, WRITES it back into the same env object the server will inherit (`env.OPENCODE_SERVER_PASSWORD = password`), and returns the matching `Authorization: Basic …` header for the client. The shared env object IS the secret channel — no file, no port, no fixed credential.

**Flow:** bridge startup → `prependOpenCodeBinToPath` fixes PATH → `configureOpenCodeServerAuth` mints the password into `procEnv` → `createOpencodeServer` spawns with that env (server reads `OPENCODE_SERVER_PASSWORD` and enforces Basic auth) → `createOpencodeClient` pins the returned header → every subsequent SDK call authenticates without per-call credential handling.

**Invariant:** the password is per-bridge-process random (never persisted, never logged); the header is derived from the SAME value written to env in the same call, so client and server can never diverge; the server binds `127.0.0.1` with `port: 0` (ephemeral), so the credential protects a loopback-only surface against other local processes, not the network.

**Probe:** `packages/harness-opencode/src/bridge/opencode-server-auth.test.ts` (2 cases): password matches `^[0-9a-f]{64}$` AND header equals `Basic base64(opencode:<env password>)`; custom username flows through. `opencode-path.test.ts` (2 cases): exact prepended PATH string; fallback path when PATH is absent. `bridge/index.test.ts` :33 mocks `prependOpenCodeBinToPath`, confirming it is a named startup dependency.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "configureOpenCodeServerAuth createOpencodeServer Authorization", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: opencode-server-auth.ts, then bridge/index.ts startup block.

## Verdict
Adopt the mint-into-shared-env + derive-header-in-one-call pattern for any host-spawned loopback service; adapt the env var names and username default; omit the bootstrap PATH prepend if your runtime resolves its binary differently. Coverage caveat: no test drives a full server spawn with these headers (the bridge integration suite binds real sockets and is excluded from edge runs upstream); the helpers themselves are unit-pinned.
