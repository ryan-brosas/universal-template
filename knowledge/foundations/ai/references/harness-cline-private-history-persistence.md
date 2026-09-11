<!-- capsule-v2 -->
# Cline private history persistence — how do you persist private session state in a sandbox so resume survives cross-process without leaking into the agent workspace?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** where does a dialect keep conversation state that must survive process death but must never be visible to (or corruptible by) the agent's own workspace?

## cline-resume-state.ts containment kernel
**Path/Symbol:** `packages/harness-cline/src/cline-resume-state.ts` (139L whole): `safeClineHistoryFileName` :12, `clineResumeStateSchema` :33, `resolveClinePrivateSessionDirectory` :41, `resolveContainedSandboxPath` :68, `persistHistoryToSandbox` :95, `pullHistoryFromSandbox` :120. Wiring: `cline-harness.ts` :152 (`lifecycleStateSchema: clineResumeStateSchema`) + :189 (`resumeHistoryFileName` forward); `cline-session.ts` :261 (resolve once per session), :302–312 (pull on resume), :379–385 (`persistHistory()`), :791/:891/:919/:957 (`data: {historyFileName: CLINE_DEFAULT_HISTORY_FILE_NAME}` stamped by every lifecycle method).

### Decisive source
```ts
export function resolveClinePrivateSessionDirectory(input: {
  readonly sandboxHomeDir: string;
  readonly sessionWorkDir: string;
  readonly sessionId: string;
}): string {
  const sessionKey = createHash('sha256').update(input.sessionId).digest('hex');
  const privateSessionDir = path.posix.join(
    input.sandboxHomeDir, '.ai-sdk', 'harness-cline', sessionKey,
  );
  const relativePath = path.posix.relative(
    input.sessionWorkDir, privateSessionDir,
  );
  if (
    relativePath === '' ||
    (!relativePath.startsWith('../') && !path.posix.isAbsolute(relativePath))
  ) {
    throw new Error(
      `Cline private session directory ${JSON.stringify(privateSessionDir)} must be outside sessionWorkDir ${JSON.stringify(input.sessionWorkDir)}.`,
    );
  }
  return privateSessionDir;
}
```

**Data Shape:** private dir = `<sandboxHome>/.ai-sdk/harness-cline/<sha256(sessionId)>` — hashing neutralizes an unsafe session id (the test passes `'../unsafe/session-id'` and expects a stable `[a-f0-9]{64}` segment). Lifecycle `data` is `z.looseObject({historyFileName: <refined basename>.optional()})` — loose so future adapter fields survive version skew. History bytes are `JSON.stringify(AgentMessage[])` written via `sandbox.writeTextFile` (creates parent dirs per the SandboxSession contract).

**Flow:** session creation resolves the private dir once → on resume, `pullHistoryFromSandbox` reads the file and returns `undefined` on missing OR unparsable content (`safeParseJSON` + `Array.isArray`), so resume degrades to a fresh conversation instead of failing `doStart` → after turns, `persistHistory()` snapshots `agent.snapshot().messages ?? currentMessages` and writes under `CLINE_DEFAULT_HISTORY_FILE_NAME` → every lifecycle method (park/suspend/stop paths) stamps `data: {historyFileName}` so the next `doStart({resumeFrom|continueFrom})` knows which file to pull.

**Invariant:** THREE containment rungs, each independently tested: (1) the filename must match `^[A-Za-z0-9][A-Za-z0-9._-]*\.json$` (rejects `../evil.json`, `a/b.json`, `.hidden.json`, `nope.txt`, `''`); (2) the private DIR must be outside `sessionWorkDir` (relative path must be `../`-prefixed or absolute) so agent-visible files can never collide with harness state; (3) `resolveContainedSandboxPath` re-resolves the final file path and re-checks containment against its dir — defense in depth even after rung 1. Fail-soft resume: unreadable/corrupt history NEVER fails `doStart`.

**Probe:** `packages/harness-cline/src/cline-resume-state.test.ts` (12 cases): filename accept/reject table, schema accept/empty/reject, stable-dir + unsafe-session-id neutralization, outside-workdir rejection, round-trip through a fake sandbox, missing-file and corrupt-content `undefined` returns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "persistHistoryToSandbox resolveClinePrivateSessionDirectory resume", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: cline-resume-state.ts first, then cline-session.ts call sites.

## Verdict
Adopt the hash-the-id + outside-workdir + re-check-containment triple for any sandboxed private state; adapt the directory namespace (`.ai-sdk/harness-cline`) and the looseObject schema fields; omit the AgentMessage JSON shape (cline-specific). Coverage note: this file was previously mislabeled "schema-only" in the pass-29 target list — the direct read disproved that; it is fully test-pinned.
