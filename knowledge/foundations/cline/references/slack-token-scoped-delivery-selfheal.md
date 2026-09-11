<!-- capsule-v2 -->
# Slack token-scoped delivery with stale-thread self-heal — how does a multi-workspace connector post with the right bot token and reap dead threads without hiding delivery failures?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** In multi-workspace OAuth mode, which bot token posts each reply, and what happens when the stored thread no longer exists on Slack's side?

## Per-call installation token wrapping + invalid_thread_ts reaping
**Path/Symbol:** `apps/cli/src/connectors/adapters/slack.ts:withSlackTeamBotToken` (:308-322), `withSlackBindingBotToken` (:291-306), `isSlackInvalidThreadTsError` (:336-344), `clearSlackBinding` (:346-360).
**Signature:** `withSlackTeamBotToken<T>(input: { slack: Pick<SlackAdapter, "getInstallation" | "withBotToken">; teamId?: string; work: () => Promise<T> }): Promise<T>`; `isSlackInvalidThreadTsError(error: unknown): boolean`.
**Data Shape:** teamId lives in the thread binding state (`binding.state?.teamId`); installations are fetched per team (`getInstallation(teamId) → { botToken }`); the error predicate matches on message TEXT (`/\binvalid_thread_ts\b/i`) because Slack API errors arrive as plain strings, not typed classes.

### Decisive source
```ts
const teamId = input.teamId?.trim();
if (!teamId) {
	return input.work();
}
const installation = await input.slack.getInstallation(teamId);
if (!installation?.botToken) {
	return input.work();
}
return input.slack.withBotToken(installation.botToken, input.work);
```
And the self-heal at the delivery edge (error re-thrown AFTER cleanup):
```ts
} catch (error) {
	if (
		isSlackInvalidThreadTsError(error) &&
		clearSlackBinding(input.bindingsPath, deliveryThreadId)
	) {
		input.logger.core.log("Cleared stale Slack binding after invalid_thread_ts", { ... });
	}
	throw error;
}
```

**Flow:** every outbound post (turn replies, schedule delivery, task-update relay) is wrapped: no teamId or no installation token ⇒ run bare (single-workspace mode); else fetch the team installation and run `work` under that bot token (test-pinned call order get → token → work). On post failure, `invalid_thread_ts` in the error text marks the stored thread as dead: the binding key is deleted from the bindings file (`clearSlackBinding` returns false when the key is already gone) and the error is RE-THROWN — delivery failure is never swallowed; only the dead binding is reaped.
**Invariant:** (1) Token scope is per-call, never ambient: work always executes inside `withBotToken`, so no cross-workspace token bleed. (2) Self-heal deletes outright (no tombstone) — the same delete-don't-tombstone discipline as the binding kernel, applied at the delivery edge. (3) Cleanup never converts a delivery failure into success: the original error propagates after reaping.
**Probe:** `apps/cli/src/connectors/adapters/slack.test.ts` — "routes Slack posts through the installation bot token for a team" (calls array `["get:T123", "token:xoxb-team-token", "work"]`), "detects Slack invalid_thread_ts errors" (matches `invalid_thread_ts`, rejects `channel_not_found`).

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.trace_path({ project: "cline", symbol: "withSlackTeamBotToken", direction: "inbound" });
```

## Verdict
Adopt per-call token scoping around every outbound call and text-predicate reaping of dead delivery targets with re-throw after cleanup. Adapt the installation store and error vocabulary to the platform (Telegram has no token scoping but has its own 400-vs-dead-chat taxonomy). Omit the chat-SDK `withBotToken` context-manager mechanics if the host SDK takes tokens as arguments. Coverage caveat: token wrapping and the error predicate are test-pinned; the two re-throw-after-clear sites are verified by source read (deliverScheduledResult :470-483, task-update relay postToThread :1140-1155).
