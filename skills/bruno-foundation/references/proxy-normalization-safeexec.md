<!-- capsule-v2 -->
# Proxy string normalization & shell-free OS probing — the small helpers every proxy-aware client gets wrong

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you turn messy human/system proxy config (`host:8080`, `localhost;127.0.0.1`, mixed separators) into usable values, and how do you query OS proxy settings without opening a shell-injection hole?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/network/system-proxy/utils/common.ts:safeExec` (:15-27), `normalizeProxyUrl` (:36-51), `normalizeNoProxy` (:53-65); platform detectors `utils/linux.ts` (258L), `utils/windows.ts` (227L), `utils/macos.ts` (122L) consume them.
**Signature:** `safeExec(bin: string, args: string[], opts: ExecFileOptions) → Promise<string | null>; normalizeProxyUrl(proxy: string, defaultProtocol = 'http') → string; normalizeNoProxy(noProxy: string | null) → string | null`.
**Data Shape:** safeExec returns trimmed stdout or null on ANY failure (never throws); normalizers are pure string→string/null.

### Decisive source
```ts
export async function safeExec(bin: string, args: string[], opts: ExecFileOptions): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync(bin, args, opts);
    return stdout.trim();
  } catch {
    return null;
  }
}
...
// Check if proxy already has a protocol (must have :// after protocol name)
if (/^[a-z][a-z0-9+.-]*:\/\/$/i.test(proxy)) return proxy;   // (regex as written: /^[a-z][a-z0-9+.-]*:\/\//i)
return `${defaultProtocol}://${proxy}`;
```

**Flow:** detectors call platform binaries via `execFile` (ARG ARRAY, never a shell string — gsettings/registry/reg/macOS networksetup output lands as data not commands), each wrapped in timeout-carrying ExecFileOptions → parse → hand results through the normalizers: scheme-less proxies get `http://` prepended ONLY when no `scheme://` prefix exists (system proxies rarely carry schemes; guessing https breaks plain proxies); no_proxy splits on `[;,\s]+`, trims, drops empties, joins with commas.
**Invariant:** exec failures are DATA (null) not exceptions — a missing gsettings binary must degrade to "no system proxy", not crash detection; normalization is idempotent (already-schemed input returned unchanged); default protocol is explicitly `http` because "cannot infer original protocol" is stated in-source as an accepted limitation rather than hidden.
**Probe:** `packages/bruno-requests/src/network/system-proxy/utils/linux.spec.ts` (:249L) pins detector behavior incl. safeExec failure paths; `common.spec.ts` (:64L) pins both normalizers.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "normalizeProxyUrl safeExec normalizeNoProxy", limit: 5 });
```

## Verdict
Adopt execFile-only OS probing with null-on-failure and idempotent scheme/no_proxy normalization. Adapt detector binaries per platform; omit Bruno's specific timeout default. Coverage caveat: none — clean coverage at pin.
