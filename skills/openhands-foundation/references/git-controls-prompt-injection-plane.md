<!-- capsule-v2 -->
# Git-controls prompt-injection plane — how does a chat UI drive git without ever running git itself?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** Where do clone/commit/push/pull/PR actions belong in an agent-chat client so the UI stays honest about failure while the agent owns execution?

## Clone launch ladder + prompt-injection menu
**Path/Symbol:** `src/components/features/chat/git-control-bar.tsx` (`handleLaunchRepository` :137–204, gating :103–115/:206–223); `src/components/features/chat/open-repository-modal.tsx` (:40–88 selection cascade); `src/components/features/conversation/conversation-git-actions-menu.tsx` (:51–99 portal + handlers); `src/utils/utils.ts` prompt builders :392–444.
**Signature:** `handleLaunchRepository(repository: GitRepository, branch: Branch): void`; `getGitPushPrompt(gitProvider: Provider): string`; menu handlers inject via `setMessageToSend(prompt)` then `onClose()`.
**Data Shape:** Repo/branch/provider resolved by priority conversation metadata > task-polling `repositoryInfo` > locally-probed `useLocalGitInfo`; folder-only conversations fall back to basename of client-side stored `selected_workspace` (NOT `workspace.working_dir`, which may be a worktree subdir).

### Decisive source
```ts
// git-control-bar.tsx onSuccess — refs, not closures: the WS status and the
// send function are read at FIRE time because V1 sendMessage can hold a
// reference to a now-closed WebSocket.
if (webSocketStatusRef.current !== "OPEN") {
  displayErrorToast(t(I18nKey.CONVERSATION$CLONE_COMMAND_FAILED_DISCONNECTED));
  return;
}
const providerName =
  repository.git_provider.charAt(0).toUpperCase() +
  repository.git_provider.slice(1);
const clonePrompt = `Clone ${repository.full_name} from ${providerName} and checkout branch ${branch.name}.`;
const pendingId = enqueuePendingMessage({ conversationId, text: clonePrompt });
scrollContext?.scrollDomToBottom();
Promise.resolve(sendRef.current({ action: "message", args: { content: clonePrompt, … } }))
  .catch((error) => { if (!pendingId) return; markPendingMessageError(pendingId, …); });
```
```ts
// utils.ts getGitPushPrompt — default-branch protection is baked INTO the
// prompt text, and PR vocabulary is provider-aware (gitlab ⇒ merge request).
return `Please push the changes to a remote branch on ${providerName}, but do NOT create a ${pr}. Check your current branch name first - if it's main, master, deploy, or another common default branch name, create a new branch with a descriptive name related to your changes. Otherwise, use the exact SAME branch name as the one you are currently on.`;
```

**Flow:** modal selects provider→repo→branch with identity cascades (changing provider resets repo+branch; changing repo resets branch) → `updateRepository` mutation FIRST → onSuccess re-checks live WS status via ref → optimistic pending bubble + scroll-to-bottom (#817) → fire-and-forget send whose rejection flips THAT pending id to error+retry link (documented trade-off: immediate feedback vs atomicity) → the AGENT reports clone failures in chat. In-conversation actions skip sending entirely: they inject prompts into the message store. Local backends suppress the Connect-Repo CTA unless a repo/workspace is known and render it inert when informational — the remote-repo flow is cloud-only; the bar returns null when it has nothing to show.
**Invariant:** The client never executes git; every action degrades to either (a) a WS chat message with an optimistically-tracked bubble whose failure path is explicit, or (b) input-store prompt injection. Gating requires `conversation && WS OPEN && !isLoadingHistory` (matches the chat-interface loading gate). The portal menu recomputes fixed position on resize + scroll CAPTURE=true and renders null until positioned (third independent occurrence of this kernel in the codebase).
**Probe:** `__tests__/components/features/chat/git-control-bar.test.tsx` (283 L WHOLE) — clone-prompt format ×4 (:101–132), visibility matrix local/cloud/workspace/history (:169–211), auto-scroll regression #817 driven through the mocked modal's captured `onLaunch` (:251–282); note the test MIRRORS `generateClonePrompt` locally instead of importing it (comment says so) — duplication to fix if you port.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "git control bar clone repository launch prompt", limit: 10 });
```

## Verdict
Adopt the two-channel split (tracked WS message for launches, input injection for quick actions), ref-based stale-closure defense, priority chain for repo metadata, and prompt-text-level guardrails with provider-aware vocabulary. Adapt the specific i18n keys and dropdowns; omit the cloud-only CTA gating if you have no local/cloud split. Coverage: no_recorded_issue on all cited paths at gen 2026-08-24T16:13:32Z.
