<!-- capsule-v2 -->
# Gateway auth isolation — provider keys never enter benchmark containers

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you give untrusted, networked task containers model access without ever shipping provider credentials into them — including the edge case where the host gateway binds loopback only?

## models.yml baseUrl rewrite + host-forwarded-env denylist + vmnet bridge forward
**Path/Symbol:** `packages/metaharness/src/runner.ts` — `writeModelsYaml`/`deriveProviders` (1222-1254), `FORWARD_ENV_DENYLIST`+`collectForwardEnv` (1355-1381), `buildHarborEnv` (1383-1423), `gatewayHealthOk` (1256-1263), `startVmnetGatewayForward` (1271-1305).
**Signature:** `collectForwardEnv(cfg: Config): Record<string, string>`; `startVmnetGatewayForward(cfg): { stop(): void } | null`.
**Data Shape:** generated `models.yml` points each provider's `baseUrl` at the gateway (`auth: oauth`, `transport: pi-native`, placeholder apiKey); forwarded env travels as one JSON blob in `OMP_BENCH_FORWARD_ENV`; denylist = container-hostile dir/session keys (`PI_CODING_AGENT_DIR`, `PI_CONFIG_DIR`, `PI_PROFILE`, `PI_PACKAGE_DIR`, `PI_SESSION_FILE`, `PI_ARTIFACTS_DIR`, `PI_TOOL_BRIDGE_*`, `PI_EVAL_LOCAL_ROOTS`).

### Decisive source
```ts
for (const [k, v] of Object.entries(process.env)) {
    if (v === undefined || !k.startsWith("PI_") || FORWARD_ENV_DENYLIST.has(k)) continue;
    out[k] = v;
}
for (const [k, v] of Object.entries(cfg.env)) out[k] = v;  // explicit --env always wins AND bypasses the denylist
...
// HTTP forward from the vmnet host address to the loopback-bound auth gateway.
// Apple Container has no host.docker.internal: containers reach the host at
// 192.168.64.1, but the pm2 gateway binds 127.0.0.1 only. The bridge interface
// only exists while a container is running, so binding retries until it appears.
const bind = (): void => {
    try { server = Bun.serve({ hostname: VMNET_HOST_IP, port, idleTimeout: 0,
        fetch(req) { const target = new URL(req.url); target.hostname = "127.0.0.1";
                     return fetch(target, { method: req.method, headers: req.headers, body: req.body, redirect: "manual" }); } });
    } catch { timer = setTimeout(bind, 2000); }
};
```

**Flow:** default route = generate `models.yml` whose provider entries rewrite `baseUrl` to the gateway URL so containers authenticate via the HOST-side gateway (which holds credentials) → health-check the gateway from the host perspective (`host.docker.internal`/vmnet IP → `127.0.0.1`) and warn-not-fail on miss → forward selected host env into the container as an opt-in allowlist-by-prefix (`PI_*` minus denylist) plus explicit overrides; values hidden in dry-run output → when the environment's bridge address differs from where the gateway binds (apple-container vmnet), start a tiny HTTP forwarder bound to the bridge IP that proxies to loopback, retrying bind every 2s until a container brings the interface up; stopped in `finally`.
**Invariant:** no credential material is written into any container — only URLs pointing back at the host; explicit user-supplied env beats both the prefix filter and the denylist (documented escape hatch); the forwarder must be torn down on every exit path (finally) or it lingers bound to a transient interface.
**Probe:** `packages/metaharness/test/runner.test.ts:38-63` — `explicit --providers is authoritative; the default derives from the model` and `collects explicit --env pairs, with an explicit value winning over a bare host-forwarded key`; gateway URL swaps per environment pinned at `:107-130`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "writeModelsYaml collectForwardEnv FORWARD_ENV_DENYLIST startVmnetGatewayForward gatewayUrl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the isolation shape for any sandboxed-agent setup: credential-holding proxy on the host, config files that point at it by URL, prefix-allowlisted env forwarding with an explicit-wins escape hatch, and a bridge-bound reverse forward when the sandbox can't reach loopback. Adapt provider entry format, env prefixes, and the specific addresses; omit pm2/Bun.serve details. Env semantics directly tested.
