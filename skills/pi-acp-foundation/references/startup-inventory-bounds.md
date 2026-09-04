<!-- capsule-v2 -->
# Startup inventory bounds — how do you keep a session-new prelude O(bounded) against pathological skill trees, and build identity you can trust?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you enumerate skills/prompts/extensions for a startup banner without letting symlink cycles or huge trees hang session/new, and how should a bundled adapter report its own provenance?

## Bounded discovery + build identity + path portability
**Path/Symbol:** `src/acp/agent.ts` (`buildStartupInfo` :2032-2266: caps :87-91 `SKILL_ITEMS_CAP=300 / PROMPT_ITEMS_CAP=100 / EXTENSION_ITEMS_CAP=100 / MAX_STARTUP_MD=64_000`, `displayPath`, realpath-visited skill stack, final truncation) + `src/build-info.ts` whole file.
**Signature:** `export const buildInfo: BuildInfo` with `{ revision, buildTime, packageVersion, isRelease, dirty }`; skill walk = iterative stack with `visited: Set<realpath>`.
**Data Shape:** tsup injects `__PI_ACP_BUILD_REVISION__/__PI_ACP_BUILD_TIME__/__PI_ACP_BUILD_DIRTY__` via `define`; dev/test fall back to `git rev-parse --short=12 HEAD` (3s spawnSync timeout) and a ≤6-level upward package.json walk ending `'0.0.0'`; `isRelease := typeof __PI_ACP_BUILD_REVISION__ === 'string'`.

### Decisive source
```ts
while (stack.length && skillsItems.length < SKILL_ITEMS_CAP) {
  const dir = stack.pop()!
  let real; try { real = realpathSync(dir) } catch { continue }
  if (visited.has(real)) continue          // symlink-cycle protection (P2-12 audit)
  visited.add(real)
  ...
}
// hard production cap AFTER per-section caps:
return text.length > MAX_STARTUP_MD
  ? `${text.slice(0, MAX_STARTUP_MD)}\n… (startup info truncated by pi-acp-jetbrain)\n`
  : text
```

**Flow:** session/new prelude now opens with the adapter's own build line (version, 12-char revision, dirty flag, build time) before the pi version probe — which itself resolves through `getPiCommand(PI_ACP_PI_COMMAND)` so version/changelog lookups match the ACTUAL spawned executable (F-024), not a hardcoded `'pi'`. All inventory paths render through `displayPath`: cwd-relative when inside the tree, else `~/`-relative via HOME, else basename (F-011 portability — no machine-specific absolute paths in prompts). Prompts/extensions reads are `.slice(0, cap)`-bounded; initialize advertises `_meta.piAcp.build`; bridge MCP clientInfo versions itself from `buildInfo.packageVersion` instead of a hardcoded string.
**Invariant:** every loop over untrusted filesystem structure has BOTH a per-section item cap AND a global markdown byte cap; cycle safety comes from visited-realpath, not depth limits; identity strings degrade to honest dev values ('dev', empty buildTime) instead of fabricating release data.
**Probe:** `npx tsx --test test/unit/startup-info-bounds.test.ts test/unit/build-info.test.ts` (bounds test creates a real symlink cycle + oversized tree and asserts bounded completion ~140ms; executed GREEN at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "buildStartupInfo SKILL_ITEMS_CAP buildInfo displayPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt double-capped inventory enumeration with realpath-visited cycles, injected-or-derived build identity, and cwd-relative prompt-path rendering. Adapt caps to your client's context budget. Omit the tsup define plumbing if your host is single-source. Both direct tests executed green at the pin (bounds suite is slow-but-bounded by design).
