<!-- capsule-v2 -->
# Announce wrapper — how do you embed an inner activity for fan-out without breaking parsers that can't nest?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How is a nested Announce built, received, and re-emitted — including the compatibility double-send for software that cannot parse nested objects?

## AnnounceActivity / RawAnnouncableActivities
**Path/Symbol:** `crates/apub/activities/src/community/announce.rs` (`Activity for RawAnnouncableActivities::receive` :47–73, `AnnounceActivity::new/send` :82–137, `Activity for AnnounceActivity::receive` :157–173, `can_accept_activity_in_community` :201–215); enum list `crates/apub/activities/src/activity_lists.rs:SharedInboxActivities` (:42–52) / `AnnouncableActivities` (:57–76).
**Signature:** `AnnounceActivity::send(object: RawAnnouncableActivities, community: &ApubCommunity, context) -> LemmyResult<()>`; `RawAnnouncableActivities { id: Url, actor: ObjectId<ApubPerson>, other: serde_json::Map<String, Value> }` (raw-catchall shape).
**Data Shape:** `AnnounceActivity { id (uuid URL with inner kind embedded: /activities/announce/<innerkind>/<uuid>), actor: community, to: [community followers], cc, kind: "Announce", object: IdOrNestedObject::NestedObject(RawAnnouncableActivities) }`. Untagged enums deserialize in ORDER — `RawAnnouncableActivities` must stay LAST in `SharedInboxActivities` or it swallows every typed variant (:50–51 comment).

### Decisive source
```rust
// announce.rs:47-72 — receiving an Announce: unwrap → verify → receive inner → re-announce
// if OUR copy of the community is local (we are the announcing instance)
let activity: AnnouncableActivities = self.clone().try_into()?;
if let AnnouncableActivities::Page(_) = activity {
  return Err(UntranslatedError::CannotReceivePage.into());   // Page rides ONLY as send-compat
}
let community = activity.community(context).await.ok();
can_accept_activity_in_community(&community, context).await?; // spam gate, see below
activity.verify(context).await?;
activity.receive(context).await?;
if let Some(community) = community && community.local {
  verify_person_in_community(&ap_id, &community, context).await?;
  AnnounceActivity::send(self, &community, context).await?;   // fan out to local followers
}

// announce.rs:119-135 — compat second send for Pleroma/Mastodon: same follower targets,
// but object = bare Page (with a bolted-on actor field) instead of the nested Create/Page
if let AnnouncableActivities::CreateOrUpdatePost(c) = object_parsed {
  let announcable_page = RawAnnouncableActivities { id: generate_activity_id(...), actor: ..., other: page_json };
  let announce_compat = AnnounceActivity::new(announcable_page, community, context)?;
  send_lemmy_activity(context, announce_compat, community, inboxes, false).await?;
}
```

**Flow:** sender wraps inner activity raw (keeps unknown fields lossless via `other` map; `TryFrom` re-injects `id`+`actor`, :176–185) and sends to community-follower targets → receiver unwraps, runs the accept gate, verifies + receives the INNER activity, then — if it hosts the community — re-wraps into a fresh Announce for its own followers. For Create/Page posts a SECOND plain Announce/Page goes to the same inboxes.
**Invariant:** the accept gate `can_accept_activity_in_community` rejects remote communities with no local followers AND no local posts/comments (`CommunityActions::check_accept_activity_in_community`, db_schema impls :342–363 — `exists(follows) OR exists(local posts) OR exists(local comments)`), so instances only process activities of communities they actually mirror; Page-as-inner-activity is a SEND-only dialect and must be refused on receipt. Enum ordering IS parsing semantics for untagged serde.
**Probe:** `crates/apub/activities/src/activity_lists.rs` `test_shared_inbox` (:111–131); `crates/db_schema/src/impls/community.rs` pins the gate SQL shape (:342–363).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "RawAnnouncableActivities", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt envelope wrapping with a raw catch-all inner payload (lossless pass-through), the single-announcer re-wrap on the hosting instance, the no-local-interest refuse gate as anti-spam, and the dual-format compatibility emit for limited consumers. Adapt the wire vocabulary to your protocol; keep untagged-enum ordering discipline if you port the Rust types verbatim. Omit Mastodon/Pleroma-specific quirks beyond the one compat send.
