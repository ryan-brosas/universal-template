<!-- capsule-v2 -->
# Shared-inbox dispatch ladder — when does an activity go to one inbox, followers, or every instance?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How does Lemmy choose recipients for a community-scoped activity, and why does a local community Announce while a remote one just forwards?

## send_activity_in_community
**Path/Symbol:** `crates/apub/activities/src/community/mod.rs:send_activity_in_community` (:53–84); report routing `report_inboxes` (:86–126); mod/admin gate `verify_mod_or_admin_action` (:132–152).
**Signature:** `send_activity_in_community(activity: AnnouncableActivities, actor: &ApubPerson, community: &ApubCommunity, extra_inboxes: ActivitySendTargets, is_mod_action: bool, context) -> LemmyResult<()>`.
**Data Shape:** `ActivitySendTargets { inboxes: HashSet<Url>, community_followers_of: Option<CommunityId>, all_instances: bool }` (`crates/db_schema/src/source/activity.rs:15–22`; constructors `to_inbox` / `to_local_community_followers` / `to_all_instances`, :26–43).

### Decisive source
```rust
// community/mod.rs:61-83 — the whole routing decision in six steps
if !community.visibility.can_federate() { return Ok(()); }          // local-only ⇒ nothing leaves
let mut inboxes = extra_inboxes;                                     // mentioned/affected users
if !is_mod_action {                                                  // mod actions skip user followers
  inboxes.add_inboxes(PersonActions::follower_inboxes(&mut context.pool(), actor.id).await?);
}
if community.local {
  // local community: wrap + fan out to ITS followers right here
  AnnounceActivity::send(activity.clone().try_into()?, community, context).await?;
} else {
  // remote community: just deliver to the community's shared inbox — IT announces onward.
  inboxes.add_inbox(community.shared_inbox_or_inbox());
}
send_lemmy_activity(context, activity.clone(), actor, inboxes, false).await?;
```

**Flow:** visibility gate (unfederable ⇒ silent no-op) → direct inboxes (mentions/affected) → user-follower inboxes unless moderation → either local-Announce-and-fan-out or forward-to-remote-community → persist via `send_lemmy_activity`. Reports additionally target: receiving community/site inbox + report-creator's home site + (local receiver only) every moderator's personal inbox + the object creator's home instance (:93–124).
**Invariant:** EXACTLY ONE instance announces a community activity — the one hosting the community. A local sender announcing AND forwarding would double-deliver; forwarding without announce would strand followers. Moderation actions deliberately bypass actor-follower fan-out. `can_federate()` is checked at BOTH send and receive boundaries so private communities never leak through any path.
**Probe:** `crates/apub/activities/src/activity_lists.rs` test `test_shared_inbox` (:111–131) parses real captured activities (Lemmy delete/accept/comment/PM/follow plus a Mastodon follow) into the dispatch enum; `crates/apub/send/src/inboxes.rs` mock tests pin the per-instance filtering side.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "send_activity_in_community", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-announcer rule for group-scoped events, the three-way recipient union resolved lazily per subscriber, the moderation-exempts-user-followers rule, and report fan-out to moderators+both home instances. Adapt "community" to your group/channel entity and inbox URLs to webhook endpoints. Omit ActivityPub wire types if you only need the routing shape.
