<!-- capsule-v2 -->
# ACP respawn strategy ladder — when a runtime process dies mid-session, which of attach / disk-replay / lossy-rerun / cold-restore recovers it?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** How does a harness adapter decide between reattaching a live bridge, replaying a coherent disk tail, rerunning a lost prompt through session resume, and cold-restoring a stopped session — without ever inventing a fresh unrelated conversation?

## The doStart respawn decider
**Path/Symbol:** `packages/harness-acp/src/v1/acp-v1-harness.ts` — `doStart` decision tree (:377–522), cold-restore execution (:624–664), session-flag wiring (:693–717); `ACPRespawnStrategy` type (:98–114).
**Signature:** `type ACPRespawnStrategy = { mode:'disk-replay'; reason; afterSeq } | { mode:'lossy-rerun'; reason; turnStartConfig; acpSessionId } | { mode:'cold-restore'; turnStartConfig; acpSessionId }`.
**Data Shape:** inputs are lifecycle state (`continueFrom` for an in-flight turn vs `resumeFrom` for a stopped session) carrying optional `bridge{port,token,lastSeenEventId,sandboxId,stateDir}`, `turnStartConfig`, `coldSession`, `acpSessionId`; output is the strategy consumed by spawn env (`BRIDGE_REPLAY_FROM_DISK=1`), channel seed (`initialLastSeenEventId` + `open({resume:true})`), and the three session flags `replayOnly`/`lossyRerun`/`turnInFlight`.

### Decisive source
```ts
// acp-v1-harness.ts:447–489 — continue + dead coords ⇒ classify the disk log
} catch (error) {
  if (isContinue) {
    const eventLog = await Promise.resolve(
      toolSafeSandboxSession.readTextFile({ path: `${bridgeStateDir}/event-log.ndjson`, ... }),
    );
    const recoveryMode = await classifyDiskLog(eventLog);
    if (recoveryMode === 'replay') {
      respawnStrategy = { mode: 'disk-replay', reason: 'completed coherent event log', afterSeq: coords.lastSeenEventId };
    } else {
      const turnStartConfig = lifecycleData.turnStartConfig;
      const acpSessionId = lifecycleData.acpSessionId;
      if (turnStartConfig == null || acpSessionId == null) {
        throw unsupported({ ..., message: 'ACP process-loss recovery is unavailable because the lifecycle state does not contain the persisted turn start configuration and ACP session identifier.', cause: error });
      }
      validateACPTurnStartConfig({ turnStartConfig, ... });
      respawnStrategy = { mode: 'lossy-rerun', reason: 'event log not replayable', turnStartConfig, acpSessionId };
    }
  }
}
// :493–521 — plain resume (no in-flight turn) ⇒ cold-restore from persisted config
if (!isContinue) {
  const coldSession = lifecycleData.coldSession; ...
  const turnStartConfig = validateACPColdSessionConfiguration({ coldSession, ... });
  respawnStrategy = { mode: 'cold-restore', turnStartConfig, acpSessionId };
}
```

**Flow:** try LIVE ATTACH first (`SandboxChannel` seeded with `coords.lastSeenEventId`; continue ⇒ `open({resume:true})`, plain resume ⇒ bare `open()`) → attach succeeds ⇒ no respawn, coordinates reused as-is → attach fails during CONTINUE ⇒ read sandbox `event-log.ndjson` ⇒ `classifyDiskLog` coherent ⇒ **disk-replay** (respawned bridge reloads the log, `replayOnly` session rejects any later `doPromptTurn`) ⇒ incoherent ⇒ **lossy-rerun** (requires persisted turnStartConfig+acpSessionId; `doContinueTurn` re-sends the ORIGINAL start frame with `recoveryMode:{type:'lossy-rerun'}`) → plain RESUME with unusable coords ⇒ **cold-restore** (revalidate coldSession against CURRENT settings, replacement bridge negotiates resume/load). Every branch converges on `createSession` with `turnInFlight` true exactly for disk-replay/lossy-rerun.
**Invariant:** recovery never silently degrades to "start a fresh conversation" — every fallback requires persisted identity evidence, and its absence is an explicit `HarnessCapabilityUnsupportedError`; `replayOnly` sessions must refuse new prompts because the replayed stream has no live ACP process behind it.
**Probe:** direct test `packages/harness-acp/src/acp-harness.test.ts:2369–2463` ("respawns a replay-only bridge for a coherent completed disk tail" — pins `BRIDGE_REPLAY_FROM_DISK='1'`, `initialLastSeenEventId===10`, `openOptions==={resume:true}`, empty sent frames, replayed `['text-delta','finish']`, later prompt rejecting `'disk replay only'`, and `data.recovery` in the next stop state); :2465–2597 ("reruns an incomplete turn only through session resume…" — incoherent one-line log ⇒ start frame carries `recoveryMode.type==='lossy-rerun'` with the ORIGINAL prompt).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "ACP respawn strategy disk-replay lossy-rerun cold-restore classifyDiskLog", limit: 10 });
```

## Verdict
Adopt the four-rung ladder ordered by information preservation (attach > replay > rerun > restore) and the rule that every rung below attach is gated on persisted non-secret evidence; adapt the disk-log classifier vocabulary to your transport's replay format; omit ACP-specific frame names. Caveat: `classifyDiskLog` itself lives in `@ai-sdk/harness/utils` (mined in the bridge-plane capsules); behavior here pinned by adapter tests, not a dedicated respawn unit test.
