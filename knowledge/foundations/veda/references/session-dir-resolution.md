<!-- capsule-v2 -->
# Session dir resolution — where do per-run artifacts live so they travel with the repo but still work outside one?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** Session artifacts (thread.json, checkpoint.yaml, response.yaml, report.yaml, selection/) must be visible to any agent operating in a project folder, yet the CLI must also work outside a git repo and under test overrides. What is the precedence ladder?

## Explicit baseDir > VEDA_HOME env > project-local .veda > user-global config home
**Path/Symbol:** `src/util/paths.ts` (`getVedaHome` :18-20, `findProjectRoot` :30-39, `getProjectVedaBase` :46-49, `getSessionDir` :51-59, `getThreadPath` :65-67, `getCheckpointPath` :71-73, `isValidSessionId` :129-132); consumers: conversation store, checkpoint store, response-save, context store.
**Signature:** `getSessionDir(sessionId: string, baseDir?: string) → string`; `findProjectRoot(dir?) → string | undefined`; `isValidSessionId(id: string) → boolean`.
**Data Shape:** session dir = `<base>/sessions/<sessionId>`; artifacts are flat files inside it (`thread.json`, `checkpoint.yaml`, `response.yaml`, `report.yaml`, `design.json`) plus the `selection/` subdir.

### Decisive source
```ts
export function getSessionDir(sessionId: string, baseDir?: string): string {
  // Explicit baseDir (tests) and an explicit VEDA_HOME override always win.
  // Otherwise prefer project-local `.veda/sessions/<session>`; fall back to
  // the user-global veda home when no project root is discoverable. Config,
  // personas, and stats stay user-global (getVedaHome) by design.
  const base = baseDir
    ?? (process.env.VEDA_HOME ? getVedaHome() : (getProjectVedaBase() ?? getVedaHome()));
  return join(base, 'sessions', sessionId);
}

export function getProjectVedaBase(dir?: string): string | undefined {
  const root = findProjectRoot(dir);
  return root ? join(root, '.veda') : undefined;
}
```
```ts
export function isValidSessionId(id: string): boolean {
  if (id.length === 0 || id.length > 64) return false;
  // Allowed: A-Za-z0-9._:-
  return /^[A-Za-z0-9._:-]+$/.test(id);
}
```
**Flow:** `findProjectRoot` walks ancestors from cwd until it finds a `.git` entry (undefined outside a repo) → `getProjectVedaBase` maps it to `<root>/.veda` → `getSessionDir` applies the four-arm precedence (explicit baseDir for tests, then VEDA_HOME env, then project-local, then user-global) → every artifact getter (`getThreadPath`, `getCheckpointPath`, `getSelectionPath`) composes onto the same session dir, so one precedence decision locates ALL run artifacts → session ids are validated (1–64 chars, `[A-Za-z0-9._:-]`) before any path is derived, blocking traversal.
**Invariant:** the precedence ladder is decided in ONE function — no consumer re-derives its own base. Project-local wins over user-global so artifacts travel with the repo (any agent in the folder sees them); user-global is the fallback so the CLI still works outside git. Config/personas/stats deliberately stay user-global (getVedaHome) — only session artifacts are project-local. The session-id grammar is enforced at store construction, before path derivation.
**Probe:** `tests/conversation/store.test.ts` (executed live at pin: 10 pass / 0 fail) pins the invalid-session-id throw and per-session isolation; `tests/util/response-save.test.ts` (executed live: 4 pass / 0 fail) pins the session-dir placement of response.yaml. The precedence arms themselves are source-pinned (no dedicated precedence test).
**Coverage caveat:** no test pins the VEDA_HOME-env vs project-local ordering directly; it is source-pinned at getSessionDir :56-58.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "getSessionDir getProjectVedaBase findProjectRoot VEDA_HOME sessions isValidSessionId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-function precedence ladder and the validate-before-derive session-id grammar. Adapt the marker (`.git` → your project marker), the project-local dir name (`.veda`), and which artifact classes stay user-global. Omit the env arm if your host has no test-override need — but keep explicit-baseDir first for testability.
