<!-- capsule-v2 -->
# Consent-gated recording state machine — how does "record only with explicit consent" survive daemon restarts and auto-mode rollover?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the preference/marker ladder that decides whether an action gets recorded?

## CDP_RECORD > config file > default-off; port-scoped on-disk active marker; auto recordings age out
**Path/Symbol:** `skills/cdp/sdk/recording.ts:envOverride` (:83-87), `autoRecordingSetting` (:98-104), `setAutoRecording` (:106-117), `activeRecording` (:119-130), `markerPath` (:78-81), `autoRecordingStale` (:281-289), `RecordingManager.observeAction` auto-lifecycle (:371-393).
**Signature:** `autoRecordingSetting(): Promise<{enabled: boolean; source: 'CDP_RECORD' | 'config' | 'default'}>` · `activeRecording(): Promise<string | undefined>`.
**Data Shape:** marker file `<root>/.active-<port>` holds the recording directory path; config `~/.browser-harness-js/recording.json` = `{"enabled":bool}` written 0600 via temp+rename; `CDP_RECORD` falsy set = `'0','false','no','off'`.

### Decisive source
```ts
async function observeAction(call, action) {
  ...
  let directory = await activeRecording();
  const setting = await autoRecordingSetting();
  if (directory && await isAutomatic(directory) && !setting.enabled) { await unlink(markerPath()); directory = undefined; }
  if (directory && await autoRecordingStale(directory))             { await unlink(markerPath()); directory = undefined; }
  if (!directory) {
    if (!setting.enabled) return;                                    // consent gate
    directory = await createRecording(`session-${stamp}`, undefined, true);
  }
```
with staleness measured against EVIDENCE mtime:
```ts
const evidence = await stat(join(directory, 'events.jsonl'));
return Date.now() - evidence.mtimeMs > idleSeconds() * 1000;        // default 180s idle rollover
```

**Flow:** every classified call re-derives state from disk (marker survives daemon restarts — it is a FILE, not process memory) → kill stale or now-unconsented AUTO recordings by unlinking their marker → no active dir + consent enabled ⇒ mint a `session-<timestamp>` auto recording → capture. Explicit `start()/stop()` write/clear the same marker; `stop()` refuses nothing but `video init --require-explicit` later rejects `meta.auto === true`.
**Invariant:** (1) Default is OFF — fresh installs never record; only a task-level request (`startRecording`) or persisted config opts in. (2) The marker is per-REPL-PORT so two daemons don't fight over one recording. (3) Consent revocation (`disable`) also removes a pending AUTOMATIC marker but never deletes an explicit recording mid-task. (4) Staleness keys off events.jsonl mtime, not wall-clock since start — a long quiet stretch after real work still rolls over correctly.
**Probe:** direct tests `skills/cdp/sdk/video.test.ts`: preference ladder (:85-104, default→config→CDP_RECORD), plus masking tests exercising `RecordingManager.start/observe/stop` end-to-end (:106-175).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "autoRecordingSetting", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-source preference ladder + disk-marker active state for any opt-in capture feature; adapt names/idle budget to your product; omit the auto-mint branch if you refuse background recording entirely (then the ladder collapses to env>config>never).
