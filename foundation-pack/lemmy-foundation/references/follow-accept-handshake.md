<!-- capsule-v2 -->
# Follow/Accept handshake — how does a remote instance subscribe to local content, and how is the follow refused?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** What is the full Follow → Accept/Reject lifecycle, and what must the follower-side Undo do to leave no dangling state?

## following plane
**Path/Symbol:** `crates/apub/activities/src/following/follow.rs` (`send_follow` :66–152, receive :154–243), `accept.rs:send_accept_or_reject_follow` (:30–96), `reject.rs`, `undo_follow.rs`; dispatch entries `crates/api/api_utils/src/send_activity.rs:SendActivityData::{FollowCommunity, FollowMultiCommunity, PrivateCommunityAcceptFollower, PrivateCommunityRejectFollower}` (:66–77).
**Signature:** `send_follow(Either<Community, MultiCommunity>, person: Person, is_following: bool, context)` (bool folds follow+undo into one entrypoint); `send_accept_or_reject_follow(community_id, person_id, follow_activity_id: Option<DbUrl>, accept: bool, context)`.
**Data Shape:** Follow activity `{ id (uuid URL), actor: person, object: community/multi id, to }`; Accept embeds the ORIGINAL follow activity as its object; the DB records `community_actions.followed_at / approved_at` timestamps.

### Decisive source
```rust
// following/follow.rs — send side: one bool drives both directions
if is_following {
  // build Follow with fresh uuid id, queue to the community's inbox
} else {
  // Undo{Follow}: look up OUR stored follow activity id — the Undo MUST reference it
}

// following/follow.rs:154-243 — receive side (remote person wants OUR community), abridged:
let community = self.object.dereference(context).await?;      // resolves + validates target
verify_person(&self.actor, context).await?;                    // not site-banned
if !community.local { return Err(UrlNotLocal)?; }
if community.visibility.can_federate() && community.posting_restricted_to_mods {
  return Err(CannotFollowRestrictedCommunity.into());          // hard refusal class
}
// persist follow row (pending approval if the community requires it) ...
if community.visibility.can_federate() {
  send_accept_or_reject_follow(...).await?;   // Accept back to the follower's inbox ...
}
// ... then IMMEDIATELY send the new content they just subscribed to:
CreateOrUpdatePage::send(new_post_snapshot, ...).await?;
```

**Flow:** remote user Follows a local community → verify actor + locality + restrictions → persist (approval-pending where enabled) → emit Accept embedding the exact follow activity id → prime the subscriber with the newest post so their timeline isn't empty → thereafter the announce fan-out reaches them. Unfollow = Undo referencing the stored follow id; private communities answer via the explicit Accept/Reject variants queued from API actions. Reject simply skips persistence and answers with Reject.
**Invariant:** Accept/Undo MUST carry the original activity's id (correlation key); follows of non-federable communities never receive Accepts; refusal reasons are typed errors, not silent drops. The "prime with latest post" step is what makes a fresh follower's feed non-empty before the next Announce.
**Probe:** fixtures `crates/apub/apub/assets/lemmy/activities/following/{follow.json,accept.json}` parsed by `crates/apub/activities/src/activity_lists.rs` test `test_shared_inbox` (:115–118); mastodon-follow compat fixture `assets/mastodon/activities/follow.json` (:130).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "send_follow", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the subscription handshake: correlation by original activity id in Accept/Undo, typed refusals, approval-pending states for gated groups, and new-subscriber priming with current content. Adapt the AP envelope to your subscription/webhook registration. Omit multi-community specifics unless porting that feature.
