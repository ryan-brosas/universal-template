<!-- capsule-v2 -->
# Private-community fetch authorization — how do you gate object READS to followers of a remote community without a shared session?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** When a private community's post is fetched, how does the server decide whether the REQUESTER's instance may see it — for local and remote communities alike?

## check_community_content_fetchable
**Path/Symbol:** `crates/apub/apub/src/http/mod.rs:check_community_content_fetchable` (:143–179), helper `get_instance_id` (:181–189); local-side query `PendingFollowerView::check_has_followers_from_instance` (`crates/db_views/community_follower_approval`); visibility gate twin `check_community_fetchable` (:135–140) used for the community object itself.
**Signature:** `async fn check_community_content_fetchable(community: &Community, request: &HttpRequest, context: &Data<LemmyContext>) -> LemmyResult<()>`.
**Data Shape:** input = community row + raw HTTP request (signature identifies a remote ACTOR ⇒ its instance); decision matrix keyed by `CommunityVisibility { Public | Unlisted | Private | LocalOnlyPublic | LocalOnlyPrivate }`.

### Decisive source
```rust
// http/mod.rs:148-178 — full visibility ladder (abridged to the Private arm)
match community.visibility {
  Public | Unlisted => Ok(()),
  Private => {
    // WHO is asking? resolve the HTTP-signature actor to an instance id
    let signing_actor = signing_actor::<SiteOrMultiOrCommunityOrUser>(request, None, context).await?;
    if community.local {
      // our own community: DB check — does the requester's INSTANCE have any approved follower?
      Ok(PendingFollowerView::check_has_followers_from_instance(
        community.id, get_instance_id(&signing_actor), &mut context.pool()).await?)
    } else if let Some(followers_url) = community.followers_url.clone() {
      // remote community we mirror: ASK the source instance by querying its followers endpoint,
      // SSRF-guarded, signed as ourselves, passing OUR actor id as the probe
      let mut followers_url = followers_url.inner().clone();
      context.is_valid_ip(&followers_url).await?;
      followers_url.query_pairs_mut()
        .append_pair("is_follower", signing_actor.id().as_str());
      let req = context.sign_request(req, Bytes::new()).await?;
      context.client().execute(req).await?.error_for_status()?;
      Ok(())
    } else {
      Err(LemmyErrorType::NotFound.into())
    }
  }
  LocalOnlyPublic | LocalOnlyPrivate => Err(LemmyErrorType::NotFound.into()),  // never federate
}
```

**Flow:** every content GET under a community checks visibility first → public/unlisted pass → private resolves the signer's home instance and either answers from the local follower-approval table or performs a signed back-check against the source instance's followers URL → local-only visibilities return NotFound unconditionally. The community OBJECT itself only requires `can_federate()` (:135–140); the CONTENT check adds the follower relationship.
**Invariant:** authorization granularity is the INSTANCE, not the user — any approved follower from your host unlocks cached content for all your users (a deliberate availability/privacy trade at AP scale); remote checks are themselves authenticated requests with SSRF validation on the target URL; "NotFound" is the universal deny so private communities are indistinguishable from missing ones.
**Probe:** no dedicated unit test at this pin (coverage caveat — the ladder is exercised via integration federation tests in `crates/api/api_crud/src/lib.rs` follow/approve flows and pinned structurally by the match arms above).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "check_community_content_fetchable", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt instance-granularity read authorization for shared-content stores, the signed back-check pattern for mirrored resources, deny-as-404, and hard local-only classes that bypass federation entirely. Adapt the follower relation to your ACL model and keep the SSRF guard when porting the outbound probe. Omit the approval-workflow internals (moderation product surface).
