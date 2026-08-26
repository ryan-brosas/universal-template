<!-- capsule-v2 -->
# Tag-keyed comment upsert — how does one comment per tool-per-directory stay updated instead of multiplying?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** How do you keep exactly one results comment per analyzer (per monorepo subdir) across repeated CI runs?

## Hidden HTML tag as idempotency key + find→update/create ladder + thread resolution state
**Path/Symbol:** identity `common/output.ts:getCommentTag` (:406-409); GitHub impl `scan/src/utils.ts:postResultsToPRComments` (:507-529) + find/create/update (:539-603); GitLab impl `gitlab/src/utils.ts:postResultsToPRComments` (:442-491) + findCommentByTag over discussions (:493-523) + lazy API client `gitlab/src/gitlabApiProvider.ts` (whole, 29L); Azure impl `vsts/src/utils.ts:postResultsToPRComments` (:406-465) + findCommentByTag over threads (:473-499).
**Signature:** `getCommentTag(toolName: string, sourceDir: string): string`.
**Data Shape:** tag = `<!-- JetBrains/qodana-action@v${VERSION} : ${toolName}, ${sourceDir} -->`, appended after `\n` to every body.

### Decisive source
```ts
// source dir needed in case of monorepo with projects analyzed by the same tool
const comment_tag_pattern = getCommentTag(toolName, sourceDir)
const body = `${content}\n${comment_tag_pattern}`
const comment_id = await findCommentByTag(client, comment_tag_pattern)
if (comment_id !== -1) {
  await updateComment(client, comment_id, body)
} else {
  await createComment(client, body)
}
```
GitLab adds a RESOLUTION state on top:
```ts
await api.MergeRequestDiscussions.resolve(projectId, mergeRequestId, discussionId, !hasIssues)
```
Azure mirrors it with thread status: `status: hasIssues ? CommentThreadStatus.Active : CommentThreadStatus.ByDesign`.

**Flow:** compose body + hidden tag → scan existing comments/discussions/threads for a body containing the tag → found ⇒ update in place (and re-resolve/re-status per platform) else create. Errors are swallowed to warnings/debug everywhere EXCEPT GitLab's finder which rethrows after logging ("Error occurred while finding comment produced by Qodana") — creation/upsert stays best-effort on all three.
**Invariant:** The tag embeds VERSION + TOOLNAME + SOURCEDIR, making the key (tool × directory × action-version): two analyzers or two monorepo dirs get separate comments, and bumping the action version intentionally starts a fresh thread rather than fighting stale formatting. The tag must be HTML-comment-hidden so it never renders. GitHub finder returns -1 (never throws) on API errors; treat "cannot search" as "create new".
**Probe:** summary fixtures (`scan/gitlab/vsts __tests__`) pin the rendered markdown the body carries; upsert functions themselves untested upstream (coverage caveat; pinned by ranges :507-603 / :442-523 / :406-499).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "findCommentByTag getCommentTag updateComment discussion", limit: 8 });
```

## Verdict
Adopt hidden-tag idempotency keys with version-stamped identity for any recurring CI comment; adapt storage (issue comments vs MR discussions vs PR threads) and add the resolve/status dimension where the host supports it.
