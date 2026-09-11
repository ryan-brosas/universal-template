<!-- capsule-v2 -->
# Reaction swap protocol — how do you flip a PR reaction (eyes → +1) without ever touching other users' reactions?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** How can a bot replace its own status reaction on a shared PR when the API offers no "list by author" filter?

## Create-first-identity + paginate + content&author-filtered delete
**Path/Symbol:** `scan/src/utils.ts:putReaction` (:615-674); constants `ANALYSIS_STARTED_REACTION='eyes'`, `ANALYSIS_FINISHED_REACTION='+1'` (:69-70); direct tests `scan/__tests__/utils.test.ts:describe('putReaction')` (:151-316).
**Signature:** `putReaction(githubToken: string, newReaction: Reaction, oldReaction: string): Promise<void>`.
**Data Shape:** `Reaction` union = GitHub's eight reaction slugs; oldReaction '' disables removal.

### Decisive source
```ts
// Create the new reaction first so its author identifies us: the token may be
// the default GITHUB_TOKEN (github-actions[bot]) or a custom PAT/App user.
let ownLogin: string | undefined
const {data: created} = await client.rest.reactions.createForIssue({...github.context.repo, issue_number, content: newReaction})
ownLogin = created.user?.login
...
if (oldReaction !== '' && oldReaction !== newReaction && ownLogin) {
  const reactions = await client.paginate(client.rest.reactions.listForIssue, {...issue_number, per_page: 100})
  for (const previousReaction of reactions.filter(r => r.content === oldReaction && r.user?.login === ownLogin)) {
    await client.rest.reactions.deleteForIssue({..., reaction_id: previousReaction.id})
  }
}
```

**Flow:** no-PR context ⇒ return before ANY api call → create the NEW reaction first and capture the response's `user.login` as self-identity (works for github-actions[bot], PATs, App tokens alike) → if an old reaction should be replaced and identity is known, paginate ALL issue reactions (per_page 100) → delete only entries matching BOTH content==old AND user.login==ownLogin; per-delete failures are caught and debugged.
**Invariant:** The bot's own login is derived from ITS OWN create-response — never from a hardcoded name or a separate `/user` call — so token-type changes don't break cleanup. Deletion is strictly conjunctive (content AND author); every failure path is non-fatal. The test suite additionally pins: equal old/new ⇒ no list/delete calls at all; null author on create ⇒ skip listing entirely; empty oldReaction ⇒ skip; non-PR context ⇒ zero octokit usage.
**Probe:** `scan/__tests__/utils.test.ts` :193-315 — six cases incl. "deletes only its own old reactions and leaves other users' alone" (asserts delete called exactly once with reaction_id 1 while id 2 other-user and id 3 new-reaction survive), rejected-delete tolerance, and `paginate`-not-`listForIssue` assertion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "putReaction createForIssue deleteForIssue own login", limit: 5 });
```

## Verdict
Adopt create-first-identity + dual-predicate deletion for any bot-managed PR decoration (reactions, labels, statuses); adapt slugs to your platform; omit nothing — this capsule's test file is the behavioral spec.
