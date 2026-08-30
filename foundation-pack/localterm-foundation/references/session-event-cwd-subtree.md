<!-- capsule-v2 -->
# Session-event cwd subtree match — which sessions' events may fire an automation?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Should a session in a subdirectory of the automation cwd trigger it?

## Exact-match-or-path-sep-prefix containment
**Path/Symbol:** `packages/server/src/session-event-manager.ts:isCwdMatch` (:148–155).
**Signature:** `(automationCwd: string, sessionCwd: string) => boolean`.
**Data Shape:** Both inputs resolved through `path.resolve`; match = equality OR `resolvedSession.startsWith(resolvedAutomation + path.sep)`.

### Decisive source
```ts
const resolvedAutomation = path.resolve(automationCwd);
  const resolvedSession = path.resolve(sessionCwd);
  return (
    resolvedSession === resolvedAutomation ||
    resolvedSession.startsWith(resolvedAutomation + path.sep)
  );
```

**Flow:** `onSessionEvent(name, sessionCwd)` iterates entries → skips those in post-run grace → re-reads live automation → requires subscribed event-name AND cwd match before arming the per-entry debounce.
**Invariant:** The `+ path.sep` suffix is load-bearing: without it `/virtual/e1x` would prefix-match `/virtual/e1`. Subdirectory sessions DO fire parent-cwd automations (test-pinned), so porters who tighten to exact-equality break nested-repo workflows.
**Probe:** `packages/server/tests/session-event-manager.test.ts` (`fires for sessions in a subdirectory of the automation cwd` :86, `ignores events from sessions in a different directory` :76).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "isCwdMatch session cwd subdirectory", limit: 10 });
```

## Verdict
Adopt verbatim including path.sep concatenation; adapt resolution semantics if your host paths are non-posix. Covered directly by both positive and negative tests.
