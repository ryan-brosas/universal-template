<!-- capsule-v2 -->
# Vote activity semantics — how does a Like carry up/down + previous state to produce idempotent score transitions?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How are votes encoded on the wire and how does the sender decide between Vote, Undo/Vote, and no-op?

## voting plane
**Path/Symbol:** `crates/apub/activities/src/voting/mod.rs` (`send_like_activity` :26–114, `Vote::receive` :116–189, `UndoVote::receive` :191–243); protocol structs `crates/apub/activities/src/protocol/voting/{vote.rs, undo_vote.rs}`; dispatch entry `SendActivityData::LikePostOrComment { object_id, actor, community, previous_is_upvote: Option<bool>, new_is_upvote: Option<bool> }` (`crates/api/api_utils/src/send_activity.rs:59–65`).
**Signature:** `send_like_activity(object_id: DbUrl, actor: Person, community: Community, previous_is_upvote: Option<bool>, new_is_upvote: Option<bool>, context) -> LemmyResult<()>`.
**Data Shape:** wire `Like { id, actor, object, cc: [community], kind: "Like", summary: Option<"Upvote"/"Downvote"> }` — the DIRECTION rides in an optional human-readable `summary` field; absence of a recognized summary defaults to upvote for backward compatibility with older Lemmy/Mastodon sends.

### Decisive source
```rust
// voting/mod.rs:29-63 (abridged) — the transition ladder decides the wire shape:
match (previous_is_upvote, new_is_upvote) {
  (_, None) => { /* vote removed: Undo{Like} referencing prior direction */ }
  (None, Some(_)) => { /* fresh vote: emit Vote with summary */ }
  _ => return Ok(()),   // same-direction re-vote ⇒ NOTHING is sent; local-only update
}

// voting/mod.rs:150-160 (Undo receive) — undoing a vote that isn't ours-or-missing is refused;
// matching direction is REQUIRED so a stale Undo can't cancel a newer opposite vote
if let Some(existing) = existing_vote {
  if existing.score != expected_score { /* direction mismatch ⇒ error */ }
}
```

**Flow:** UI toggles map to `(previous, new)` pairs → identical pairs short-circuit (no network churn) → removals become Undo/Like carrying the OLD direction → creations/switches become Vote with `summary` set (a switch emits Undo-old THEN Vote-new) → receivers validate actor/community/visibility then apply or remove the score row keyed by (person, post/comment).
**Invariant:** vote identity = (actor, object); direction lives in `summary` and must MATCH between a Like and its Undo or the undo errors — this prevents out-of-order federation from flipping scores. Same-state transitions never hit the wire. Scores are derived state; activities are the source of truth.
**Probe:** fixtures `crates/apub/apub/assets/lemmy/activities/voting/{vote.json,undo_vote.json}` parsed via the shared-inbox test battery (`crates/apub/activities/src/activity_lists.rs`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "send_like_activity", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt transition-based event emission (diff old/new state, skip no-ops, pair every create with a direction-checked undo). Adapt the summary-field hack to explicit enum fields in your own schema. Omit score-aggregation queries (db_views plane).
