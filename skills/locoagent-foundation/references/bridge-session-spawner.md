<!-- capsule-v2 -->
# Child session spawner — env-var auth ladder, NDJSON activity parsing, and token delivery via stdin

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you spawn a headless CLI child that authenticates to a session stream, report its activity upward, and rotate its credentials mid-flight?

## Path/Symbol
**Path/Symbol:** `src/bridge/sessionRunner.ts` — `safeFilenameId` (:24-26, strips traversal chars from IDs used in filenames), `createSessionSpawner` (:248-548): scriptArgs node-vs-binary fix (:45-54), debug/transcript file derivation (:255-285), child env block (:306-323), stderr ring buffer (:352-366), stdout NDJSON loop (:369-446), done-status resolution (:448-480, signal→interrupted / 0→completed / else failed), kill vs forceKill separate flags (:491-518), `updateAccessToken` stdin frame (:527-542); activity extraction `extractActivities` (:107-200), first-user-message filter `extractUserMessageText` (:207-234).
**Signature:** `createSessionSpawner(deps) → SessionSpawner; spawn(opts, dir) → SessionHandle`.
**Data Shape:** handle exposes ring buffers (`activities` ≤10, `lastStderr` ≤10), live accessToken (mutable), and a `done: Promise<'completed'|'failed'|'interrupted'>`.

### Decisive source
```ts
const env: NodeJS.ProcessEnv = {
  ...deps.env,
  // Strip the bridge's OAuth token so the child CC process uses
  // the session access token for inference instead.
  CLAUDE_CODE_OAUTH_TOKEN: undefined,
  CLAUDE_CODE_ENVIRONMENT_KIND: 'bridge',
  CLAUDE_CODE_SESSION_ACCESS_TOKEN: opts.accessToken,
  ...(opts.useCcrV2 && {
    CLAUDE_CODE_USE_CCR_V2: '1',
    CLAUDE_CODE_WORKER_EPOCH: String(opts.workerEpoch),
  }),
}
...
handle.writeStdin(jsonStringify({
  type: 'update_environment_variables',
  variables: { CLAUDE_CODE_SESSION_ACCESS_TOKEN: token },
}) + '\n')
```

**Flow:** spawn args must include the SCRIPT PATH before CLI flags on npm installs or node eats `--sdk-url` as a node option (#28334). The env ladder is the security boundary: parent OAuth token explicitly UNSET (child must not inherit inference credentials), replaced by the session-scoped access token; v2 adds transport selector + epoch. Stdout lines parse twice per line by design (activity extractor + control_request/first-user-message detector) because each path stays self-contained. Token rotation arrives as an `update_environment_variables` stdin frame — the child's StructuredIO applies it to process.env so the next refreshHeaders picks it up. forceKill uses its OWN flag because `child.killed` is set at SIGTERM-send time, not exit.

**Invariant:** (1) Never let the child inherit the parent's OAuth token — strip it in the env literal. (2) kill()/forceKill() idempotence flags are separate; reusing child.killed skips the needed SIGKILL. (3) Session IDs go into filenames only through safeFilenameId (server-supplied strings). (4) First-user-message detection excludes `parent_tool_use_id`/isSynthetic/isReplay — tool results and replayed history would otherwise become session titles.

**Probe:** coverage caveat — no upstream unit tests for this file. Deterministic pins: `grep -n "bad option: --sdk-url" src/bridge/sessionRunner.ts` (:53); `grep -n "CLAUDE_CODE_OAUTH_TOKEN: undefined" src/bridge/sessionRunner.ts` (:310); `grep -n "sigkillSent" src/bridge/sessionRunner.ts` (:349,:507); graph resolves `locoagent.src.bridge.sessionRunner.createSessionSpawner` :248-548 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createSessionSpawner updateAccessToken extractActivities safeFilenameId extractUserMessageText", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the spawner skeleton wholesale for orchestrating credentialed headless children. Adapt the exact env-var names to your SDK; omit transcript files if you have no forensics need.
