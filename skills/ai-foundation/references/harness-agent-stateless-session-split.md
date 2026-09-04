<!-- capsule-v2 -->
# Harness agent stateless/session split — where does agent-run state live when one definition drives many third-party runtimes?

**Source:** Vercel AI SDK Apache-20 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** If an "agent" object must be constructed once and shared, but every conversation needs isolated lifecycle (resume across processes, sandbox ownership), which parts go on the definition vs the session handle?

## Stateless definition, caller-owned sessions
**Path/Symbol:** `packages/harness/src/agent/harness-agent.ts` — `HarnessAgent` class doc + fields (:73–205), `createSession` (:219–476), `cleanupAfterStartFailure` (:955–963).
**Signature:** `new HarnessAgent(settings)`; `createSession(options?: { sessionId?, resumeFrom?, continueFrom?, sandboxSession?, abortSignal? }): Promise<HarnessAgentSession>`.
**Data Shape:** Definition holds adapter, merged tools (builtins spread UNDER user tools so user wins key collisions, :179–182), stop conditions, sandbox config, resolved permission mode. Session holds sessionId, underlying adapter session, sandboxSession, pending approval/result maps, turn state.

### Decisive source
```ts
if (resumeFrom != null && continueFrom != null) {
  throw new Error('HarnessAgent.createSession: pass either `resumeFrom` or `continueFrom`, not both.');
}
...
const ownsSandboxLifecycle = providedSandboxSession == null;   // :254 — decided ONCE at entry
...
} catch (error) {
  await cleanupAfterStartFailure({ sandboxSession, ownsSandboxLifecycle });
  throw error;
}
// cleanupAfterStartFailure: if (!input.ownsSandboxLifecycle) return;  // caller-owned never stopped
```

**Flow:** constructor validates sandbox settings + throws `HarnessCapabilityUnsupportedError` when a non-`allow-all` permission mode is combined with builtins on a harness without `supportsBuiltinToolApprovals` → every failure path inside createSession (bootstrap apply, ensureSandboxDirectory/onSession, doStart) funnels into `cleanupAfterStartFailure`, which stops the sandbox only when harness-owned.
**Invariant:** The definition NEVER holds per-conversation data; the session handle is the ONLY owner of runtime/sandbox references; a caller-provided sandboxSession is never stopped or destroyed by the framework (ownership decided once, from whether the session was passed in).
**Probe:** deterministic probes: `grep -c 'pass either .resumeFrom. or .continueFrom., not both.' packages/harness/src/agent/harness-agent.ts` → `1`; `grep -c ownsSandboxLifecycle packages/harness/src/agent/harness-agent.ts` → `8`; direct test `harness-agent.test.ts:1736` ("does not stop a provided sandbox session when harness startup fails").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "HarnessAgent createSession", limit: 4, fields: ["signature", "lines"] });
// verified live @9d9a73f — rank#1 HarnessAgent.createSession :219-476
```

## Verdict
Adopt the stateless-definition/caller-owned-session split with XOR resume gates and single-point ownership decision; adapt tool-merge order and capability-error naming to host; omit the specific deprecation shim (`onSandboxSession` console.warn). Runner caveat: vitest blocked (no node_modules) — probes are byte-exact greps plus live graph retrieves.
