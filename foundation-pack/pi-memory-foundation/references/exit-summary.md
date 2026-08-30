<!-- capsule-v2 -->
# Exit summary — gated, timeout-bounded auto-summarization that writes only real content

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent auto-generate a session exit summary into the daily log without polluting it with boilerplate, blocking quit on a hanging provider, or firing on non-final lifecycle transitions?

## Exit summary
**Path/Symbol:** `index.ts:formatExitSummaryReason` (306–310), `truncateConversationForSummary` (312–327), `buildExitSummaryPrompt` (329–348), `formatExitSummaryEntry` (350–358), `getSessionBranch` (360–368), `resolveExitSummaryApiKey` (370–388), `resolveExitSummaryModel` (395–417), `generateExitSummary` (419–487), `getQmdUpdateMode` (489–495), `shouldSummarizeLifecycleTransitions` (497–500), `isExitSummaryEnabled` (506–509), `isExitSummaryEmpty` (518–525), `getExitSummaryTimeoutMs` (535–538), `shouldSkipExitSummaryForReason` (540–544).
**Signature:** `generateExitSummary(ctx): Promise<ExitSummaryResult>`; `isExitSummaryEmpty(summary): boolean`; `getExitSummaryTimeoutMs(): number`; `shouldSkipExitSummaryForReason(reason): boolean`.
**Data Shape:** `ExitSummaryResult = { summary: string | null; error?: string; hasMessages: boolean }`. `EXIT_SUMMARY_MAX_CHARS = 80_000`, `EXIT_SUMMARY_MIN_MESSAGES = 4`, default timeout 10s. `ExitSummaryReason = "ctrl+d" | "slash-quit" | "session-end"`.

### Decisive source
```ts
// generateExitSummary (433-435): curated-write gate — trivial sessions get no summary
if (messages.length < EXIT_SUMMARY_MIN_MESSAGES) return { summary: null, hasMessages: false };

// isExitSummaryEmpty (518-525): all-"None." summaries are boilerplate → filtered out
const contentLines = summary.split("\n").map(l => l.trim()).filter(l => l.length > 0 && !l.startsWith("#"));
if (contentLines.length === 0) return true;
return contentLines.every(l => /^none\.?$/i.test(l.replace(/^[-*+]\s*/, "")));

// shouldSkipExitSummaryForReason (540-544): /reload,/new,/resume,/fork are not final exits
if (shouldSummarizeLifecycleTransitions()) return false;
return ["reload", "new", "resume", "fork"].includes(reason);
```

**Flow:** (1) On `session_shutdown`, skip entirely if the reason is a lifecycle transition (reload/new/resume/fork) or exit summaries are disabled. (2) `generateExitSummary` gates on ≥4 messages, resolves the model (env override or session model) and API key, serializes the conversation (truncated to 80K end-mode), and calls the LLM with a strict `### Decisions / Lessons Learned / Notes / Follow-ups` prompt. (3) The caller races the summary against a self-imposed timeout (default 10s) so a hanging provider never blocks quit. (4) Only a non-empty, non-all-"None." summary is appended to today's daily log with a `<!-- ts [sid] -->` stamp.

**Invariant:** a trivial or all-"None." session never pollutes the daily log (which is re-injected every session start and indexed by qmd); shutdown never blocks indefinitely on a provider; lifecycle transitions stay fast by default.

**Probe:** `test/unit.test.ts` — `exit summary configurability` describe (:1573): `PI_MEMORY_EXIT_SUMMARY=0 skips the exit summary on real quit` (:1622), `PI_MEMORY_EXIT_SUMMARY_MODEL routes the summary to the configured model` (:1646), `unresolvable PI_MEMORY_EXIT_SUMMARY_MODEL falls back to the session model` (:1663); `isExitSummaryEmpty` describe (:1680): `treats all-None summaries as empty` (:1681), `tolerates formatting variations` (:1695), `keeps summaries with any real content` (:1701); `exit summary shutdown timeout` describe (:1717): `session_shutdown stays responsive when summary generation hangs` (:1773), `getExitSummaryTimeoutMs parses env with fallback to default` (:1762); `session_shutdown with reason=reload skips exit summary entirely` (:1465), `session_shutdown skips trivial sessions without attempting a summary` (:1488). Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "generateExitSummary isExitSummaryEmpty getExitSummaryTimeoutMs shouldSkipExitSummaryForReason", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ≥4-message gate, the strict four-heading summary prompt, the `isExitSummaryEmpty` boilerplate filter, the self-imposed shutdown timeout, and the lifecycle-transition skip. Adapt the model/env names, the timeout, and the daily-log append format to the host. Omit the Pi `sessionManager`/`modelRegistry`/`ui` integration details unless a target needs them.
