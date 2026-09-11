<!-- capsule-v2 -->
# Client-impersonation version discovery — how do you keep a spoofed client UA current enough for model gating?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When a backend gates models on client version, how do you track the real client's version without coupling startup to a network fetch?

## env override → manifest probe (silent, once) → pinned fallback
**Path/Symbol:** `packages/catalog/src/wire/gemini-headers.ts:getAntigravityVersion` (:45), `parseAntigravityManifestVersion` (:53), `ensureAntigravityVersion` (:69), `getAntigravityUserAgent` (:93), `ANTIGRAVITY_MODEL_WIRE_PROFILES` (:121); Gemini CLI UA at top of file.
**Signature:** `ensureAntigravityVersion(fetcher?, signal?): Promise<void>`; `getAntigravityUserAgent(): string`; `getAntigravityModelWireProfile(wireModelId): {modelEnum?, maxOutputTokens} | undefined`.
**Data Shape:** UA format captured from the real 2.8.0 hub client: `` antigravity/hub/<version> (aidev_client; os_type=darwin; arch=arm64; cl=<changelist>) `` — os/arch PINNED to the reference client regardless of host platform.

### Decisive source
```ts
// Success cached process-lifetime; failures SILENT (the pinned fallback
// stays valid) and clear the in-flight cache so a later call retries.
// Skipped entirely when PI_AI_ANTIGRAVITY_VERSION is set.
antigravityVersionFetch = (async () => {
  try {
    const timeoutSignal = AbortSignal.timeout(5_000);
    /* … manifest fetch … */
    if (response.ok) discoveredAntigravityVersion = parseAntigravityManifestVersion(await response.text());
  } catch { /* silent */ }
  finally { if (!discoveredAntigravityVersion) antigravityVersionFetch = null; }
})();

// The backend does NOT validate cl (verified live: stale/zero/absent cl all
// pass model gating on daily-cloudcode-pa; only the VERSION gates).
// Claude wire ids cap maxOutputTokens at 64000 or the backend 400s.
"claude-sonnet-4-6": { maxOutputTokens: 64000 },
```

**Flow:** request assembly calls `ensureAntigravityVersion()` early → in-flight promise shared (single flight per process) → version resolved env > discovered > default → UA rebuilt per call from current version → per-wire-id profiles looked up by the ROUTED upstream id (post effort-routing, not logical id); checkpoint-only ids intentionally absent (provider emits agent requests only).
**Invariant:** (1) version discovery never blocks longer than 5s and never fails a request — worst case is the pinned fallback; (2) the yaml manifest parser accepts only strict `x.y.z` versions from a well-formed `version:` line; (3) wire profiles key on post-routing ids because routing picks the actual upstream SKU; (4) Gemini CLI UA format (`GeminiCLI/v/model (platform; arch; terminal)`) unlocks higher rate limits — same impersonation economics.
**Probe:** coverage caveat: no direct unit test pins the manifest parser or profile table (network/version-dependent); contract verified by live-capture comments in source (`daily-cloudcode-pa` captures cited inline). Nearest deterministic checks: `test/cursor-discovery.test.ts` / `test/codex-discovery.test.ts` exercise the sibling impersonation flows.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "getAntigravityVersion ensureAntigravityVersion ANTIGRAVITY_MODEL_WIRE_PROFILES", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the single-flight silent version probe with pinned fallback and post-routing wire-profile keys; adapt UA formats/profile tables to whatever client you must emulate (and re-verify against live traffic); omit entirely if your endpoints don't gate on client version. Coverage caveat recorded above.
