<!-- capsule-v2 -->
# Extension path & identity anchors — where do all on-disk artifacts live, and how do name constants keep config paths, status keys, and log lines consistent?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** An extension writes config, auth, images, and queue claims under a host agent directory — how do you anchor every path to ONE env-overridable root and namespace user-visible strings from one identity module?

## Path + identity anchors
**Path/Symbol:** `src/paths.ts` whole (:1-17) — `expandTildePath` :4-8, `piAgentDir` :10-13, `resolveUserPath` :15-17; `src/identity.ts` whole (:1-7); composition `src/config.ts:configPaths` (:559-564).
**Signature:** `piAgentDir(env = process.env, home = homedir()): string`; `expandTildePath(path: string, home = homedir()): string`; `logPrefix(): string`.
**Data Shape:** Every function takes injectable `env`/`home` defaults so tests never touch the real filesystem or environment.

### Decisive source
```ts
export function expandTildePath(path: string, home = homedir()): string {
  if (path === "~") return home;
  if (path.startsWith("~/") || path.startsWith("~\\")) return join(home, path.slice(2));
  return path;                                   // anything else passes through untouched
}

export function piAgentDir(env = process.env, home = homedir()): string {
  const configuredDir = env.PI_CODING_AGENT_DIR?.trim();
  return configuredDir ? expandTildePath(configuredDir, home) : join(home, ".pi", "agent");
}

// config.ts — both config layers join the SAME basename:
return {
  project: join(cwd, ".pi", "extensions", CONFIG_BASENAME),
  global:  join(piAgentDir(env, home), "extensions", CONFIG_BASENAME),
};
```

**Flow:** `piAgentDir` is the single root anchor — consumers: codex-auth (OAuth auth.json), configPaths (global config layer), image.resolveSaveDir (via resolveUserPath for cwd-relative saves), live.queue.liveQueueDirectory (floor-claim files). Identity constants flow outward in parallel: CONFIG_BASENAME into both config layers, STATUS_KEY ("better-openai") keys the footer's setStatus/setStatusWidget lines, logPrefix() prefixes read/write failure warnings (config.ts:600/:759).
**Invariant:** Tilde expansion handles exactly three shapes (`~`, `~/`, `~\`) and passes everything else through untouched — no silent resolution of bare names; PI_CODING_AGENT_DIR is trimmed BEFORE expansion so whitespace can't poison the path; unknown fields aside, the project/global split means one cwd-scoped file plus one home-scoped file, both named identically.
**Probe:** `tests/config.test.ts` (:86-92 — `configPaths("/project","/home/alice",{PI_CODING_AGENT_DIR:"~/custom-agent"}).global === "/home/alice/custom-agent/extensions/pi-better-openai.json"` pins override+tilde+basename in one assertion; :45 pins CONFIG_BASENAME literal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "piAgentDir expandTildePath CONFIG_BASENAME STATUS_KEY logPrefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one env-overridable agent-dir anchor with injectable env/home and exact-shape tilde handling; centralize basename/status-key/log-prefix constants. Adapt the dir name and env var to your host. Omit pi-specific layout conventions beyond the pattern. Caveat: paths.ts has no dedicated unit test — pinned indirectly through configPaths assertions above; STATUS_KEY/logPrefix consumer sites are source-pinned only.
