<!-- capsule-v2 -->
# Quiet vs loud config reads — the request path dies on corrupt config; the settings UI falls back to defaults

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** Should a malformed JSON config file crash the provider or degrade to defaults — and can both behaviors coexist legitimately?

## Quiet vs loud config reads
**Path/Symbol:** `src/config.ts:175-199` (`readConfigFile`, loud); `readConfigFileQuiet` :201-208 (quiet wrapper); loud consumers `loadLayers` :493/:498 (home + project layers of the full ladder); quiet consumers `loadProjectKimiCodeConfig` :539-546 and `loadHomeKimiCodeConfig` :548-555 (settings-draft loaders); bootstrap/save `ensureKimiCodeConfig` :531-537, `saveKimiCodeConfigFile` :565-568.
**Signature:** `readConfigFile(path): Record<string, unknown>` throws ConfigError on read failure, invalid JSON, or non-object root; `readConfigFileQuiet(path)` catches, logs, returns `{}`.
**Data Shape:** missing file ⇒ `{}` (both variants — absence is never an error); unreadable/malformed/non-object ⇒ throw vs log-and-empty.

### Decisive source
```ts
function readConfigFile(path: string): Record<string, unknown> {
  if (!existsSync(path)) return {};
  ...
  try {
    const parsed = JSON.parse(contents) as unknown;
    if (isRecord(parsed)) return parsed;
    throw new ConfigError("config file must be a JSON object", path);
  } catch (error) {
    if (error instanceof ConfigError) throw error;
    throw new ConfigError(`invalid JSON: ${...}`, path);
  }
}

function readConfigFileQuiet(path: string): Record<string, unknown> {
  try {
    return readConfigFile(path);
  } catch (error) {
    console.error(`[kimi-coding] failed to read config file ${path}:`, error);
    return {};
  }
}
```

**Flow:** one primitive owns all three failure modes (absent / unreadable / malformed /
non-object); the quiet variant is a thin policy wrapper. The FULL ladder
(loadKimiCodeConfig → loadLayers) reads loudly: a corrupt home or project file stops the
provider with a precise ConfigError because silently ignoring it would change model
behavior invisibly. The single-layer draft loaders used by the settings menu
(index.ts:208-212 calls loadHome/loadProject per scope before opening the TUI) read
quietly so the editor can still open on a corrupt file and re-save valid content.
Write-side posture: `ensureKimiCodeConfig` writes the materialized default only when the
file is absent and is idempotent (returns true only on first creation);
`saveKimiCodeConfigFile` mkdir -p's the directory and RE-VALIDATES with the concrete path
before writing, appending a trailing newline.
**Invariant:** absence ≠ corruption — `{}` for missing files in both modes; corruption is
loud on the request path, quiet-with-stderr-marker `[kimi-coding]` on preview paths;
validation always precedes write.

**Probe:** `tests/config.test.ts:166-177` — home file containing `{` makes
loadKimiCodeConfig throw ConfigError with message containing "invalid JSON" (loud side);
:199-206 — ensure bootstraps once then reports false (idempotence). Executed GREEN this
pass (config suite 12/12).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "read config file quiet malformed JSON fallback", limit: 5 });
// observed: readConfigFileQuiet #1 (-29.45), readConfigFile #2 (-22.3)
```

## Verdict
Adopt the split: fail loud wherever config drives requests, fail soft (log marker +
defaults) wherever a human is about to edit the file anyway. Adapt the log prefix to your
host's log vocabulary and keep "missing" distinct from "corrupt". Omit the quiet variant
only if you have no interactive settings surface.
