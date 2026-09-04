<!-- capsule-v2 -->
# Delete/Undo verification matrix — who may delete what, per object type, and what does receiving a Delete actually do?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How is destructive-activity authorization decided per deletable type, and how does the same code path serve user-delete vs mod-remove (Delete vs Remove semantics)?

## verify_delete_activity / receive_delete_action
**Path/Symbol:** `crates/apub/activities/src/deletion/mod.rs` — sender `send_apub_delete_in_community` (:59–107, PM :109–146, user :148–171), `DeletableObjects` enum + `read_from_db` (:173–213), verifier `verify_delete_activity` (:215–267) + `verify_delete_post_or_comment` (:269–285), receiver `receive_delete_action` (:288–372).
**Signature:** `verify_delete_activity(activity: &Delete, is_mod_action: bool, context) -> LemmyResult<()>`; the `reason: Option<String>` field IS the mod/user discriminator on send (`is_mod_action = reason.is_some()`, :72).
**Data Shape:** `DeletableObjects { Community | Person | Comment | Post | PrivateMessage }`, resolved from an AP id by trying each `read_from_id` in turn (:186–201).

### Decisive source
```rust
// deletion/mod.rs:215-231 — per-type authorization ladder (abridged)
match object {
  DeletableObjects::Community(community) => {
    verify_visibility(&activity.to, &[], &community)?;
    if community.local {   // remote case would try to fetch the already-deleted community and fail
      verify_person_in_community(&activity.actor, &community, context).await?;
    }
    verify_mod_action(...).await?;            // community deletion is ALWAYS a mod/admin action
  }
  DeletableObjects::Person(person) => {
    verify_is_public(&activity.to, &[])?;
    verify_person(&activity.actor, context).await?;          // also fails on site-banned actors
    verify_urls_match(person.ap_id.inner(), activity.object.id())?;  // only self-deletion
  }
  ...
}
// deletion/mod.rs:277-283 — post/comment fork: mod path vs owner path
if is_mod_action { verify_mod_action(actor, object_id, community, context).await? }
else {
  verify_person_in_community(actor, community, context).await?;
  verify_domains_match(actor.inner(), object_id)?;  // actor domain == object domain ⇒ same origin
}

// deletion/mod.rs:296-312 — receiving a community Delete ECHOES it onward before applying locally
DeletableObjects::Community(community) => {
  if community.local {
    let mod_ = actor.dereference(context).await?.deref().clone();
    send_apub_delete_in_community(mod_, c, object.clone(), None, true, None, context).await?;
  }
  Community::update(pool, community.id, &CommunityUpdateForm { deleted: Some(deleted), .. }).await?;
```

**Flow:** senders pick Delete (user self-action) vs mod-flavored variant by presence of `reason`; receivers resolve the object id to a concrete type and run its ladder: community ⇒ mod-only (+ local-only person check), person ⇒ self-only via URL equality + ban check, post/comment ⇒ mod OR (in-community + same-origin-domain), PM ⇒ actor-domain-must-match-object. Receiving applies soft-delete flags ONLY when the flag would change (`deleted != post.deleted`, :334) — idempotent re-delivery is a no-op — and a received community/user deletion is re-federated by the hosting instance so followers learn about it.
**Invariant:** authorization keys off object TYPE, not activity shape; domain-equality (`verify_domains_match`) substitutes for ownership checks where ids are origin-scoped; every DB write is conditional so duplicate Deletes/Restores stay idempotent; deleted-community fetch loops are dodged by checking `community.local` before dereferencing.
**Probe:** `crates/apub/apub/assets/lemmy/activities/deletion/*.json` fixtures parsed by `test_shared_inbox` (`crates/apub/activities/src/activity_lists.rs:113–114`); wire-shape round-trip pinned in-capsule via asset files (delete_user.json, delete.json, undo_delete.json).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "verify_delete_activity", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the type-keyed authorization matrix, reason-presence as the mod/user signal, domain-equality as cheap same-origin proof, conditional-flag idempotent application, and re-echo of destructive events by the owning instance. Adapt the five object types and the specific verifier helpers to your domain model. Omit the plugin-hook purge pipeline (host-specific account deletion side effects).
