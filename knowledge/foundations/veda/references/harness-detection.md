<!-- capsule-v2 -->
# Harness detection — how do you detect installed CLI harnesses and bake a stable default model?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** An init command must detect which agent-backend CLIs exist on the user's machine and pick a default model to bake into generated skills. How is detection ordered, probed, and kept stable across alias-table churn?

## Priority-ordered PATH probing with full-model-name defaults
**Path/Symbol:** `src/agent/detect.ts` (whole, 116L): `isCommandAvailable` (:61-72), `detectBackends` (:75-86), `pickDefaultModel` (:90-97), `listPiModels` (:101-116); tables `BACKEND_BINARIES` (:41-48), `BACKEND_DEFAULT_MODEL` (:51-58), `DETECTION_ORDER` (:60).
**Signature:** `detectBackends() → DetectedBackend[] {name, command}`; `pickDefaultModel(backends?) → DefaultModel {model, backend} | undefined`; `listPiModels() → string[]`.
**Data Shape:** detection order is a fixed array `['codex', 'claude-code', 'pi', 'droid', 'agy']`; each backend maps to its binary name (`codex→'codex'`, `claude-code→'claude'`, …) and a full default model id (never an alias).

### Decisive source
```ts
export function isCommandAvailable(command: string): boolean {
  try {
    const { execSync } = require('child_process');
    execSync(`command -v ${command}`, { stdio: 'ignore', shell: true });
    return true;
  } catch {
    return false;
  }
}

export function pickDefaultModel(backends?: DetectedBackend[]): DefaultModel | undefined {
  const installed = backends ?? detectBackends();
  if (installed.length === 0) return undefined;
  // First in priority order wins.
  return BACKEND_DEFAULT_MODEL[installed[0].name];
}
```
**Flow:** `detectBackends` walks `DETECTION_ORDER`, probing each binary with `command -v` in a shell (so the user's real PATH — nvm, brew, etc. — is respected) and returning hits in priority order → `pickDefaultModel` takes the FIRST installed backend's entry from `BACKEND_DEFAULT_MODEL` → `listPiModels` reads `~/.pi/agent/models.json` leniently (missing file or parse error ⇒ `[]`) and projects each provider's models into `pi/<provider>/<id>` strings.
**Invariant:** the baked default is always a FULL model name, never an alias — init output survives alias-table churn (aliases are a resolution-time convenience, not a storage format); detection is read-only and never throws (probe failure ⇒ "not installed").
**Probe:** `tests/agent/detect.test.ts` (executed live at pin: 3 pass / 0 fail) pins the exported surface; the PATH probe itself is environment-dependent and asserted only structurally.
**Coverage caveat:** `command -v` via `execSync` costs a process spawn per backend — fine for init-time, wrong for hot paths; a port on Windows needs a different probe (`where`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "detectBackends pickDefaultModel isCommandAvailable listPiModels init default model", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt priority-ordered `command -v` probing and full-model-name defaults baked at init. Adapt the binary table, priority order, and probe mechanism to your host's shells. Omit the pi models.json reader if you have no pi-equivalent provider.
