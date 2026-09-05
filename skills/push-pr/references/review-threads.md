# Review threads

"Address the PR review comments" authorizes exactly the review workflow, read the threads, implement fixes, reply in-thread, resolve addressed threads, and no other GitHub writes (no unrelated comments, deletions, metadata changes).

1. **Enumerate threads.** REST: `gh api repos/OWNER/REPO/pulls/NUMBER/comments` (review comments). GraphQL: `repository.pullRequest.reviewThreads` for thread state.
2. **Distinguish ids.** A top-level review comment has `in_reply_to_id: null`; its **database id** is what replies anchor to. Thread state lives on the GraphQL **review-thread node id** (`PRRT_…`), a different identifier from the REST comment id. Never conflate them.
3. **Implement and verify** the feedback locally (project gates) before replying.
4. **Reply in-thread**, never as a new top-level comment: `POST /repos/OWNER/REPO/pulls/NUMBER/comments` with `in_reply_to` = the top-level comment's database id. Pass the body through a file/stdin, `gh api --input <file>` with the payload JSON (put GraphQL query AND variables inside the JSON body; `-f`/`-F` fields do not bind GraphQL variables when `--input` is used, verified live 2026-08-30).
5. **Resolve** with GraphQL `mutation { resolveReviewThread(input: {threadId: "PRRT_…"}) { thread { isResolved } } }`, only when the feedback is addressed or deliberately dispositioned AND the requested workflow authorizes resolution. Feedback needing reviewer confirmation stays unresolved; posting a reply is never resolution.
6. **Reply format:** `Updated in <sha>.` + what changed + verification when relevant. No invented SHAs; no social filler ("great catch", "thanks").

Verified live on this repository (PR #10, 2026-08-30): REST list returned `{id, in_reply_to_id: null, pull_request_review_id}`; GraphQL reviewThreads returned `PRRT_…` node ids whose `comments.nodes[].databaseId` map to the REST ids. Re-verify endpoint shapes before relying on them, do not freeze these recipes.
