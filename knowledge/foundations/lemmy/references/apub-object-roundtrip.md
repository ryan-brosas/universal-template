<!-- capsule-v2 -->
# AP object round-trip — how do DB rows become ActivityPub JSON and back without losing fields?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** What is the conversion contract between database rows and wire objects (Page/Note/Person/Group), including which fields are optional and how unknown inbound fields survive?

## ApubObject trait + protocol structs
**Path/Symbol:** `crates/apub/objects/src/objects/post.rs:ApubPost` (:48–486, largest converter: `to_apub`, `from_apub`, verify ladder), siblings `comment.rs` (334 L), `community.rs` (326 L), `person.rs` (271 L), `private_message.rs` (252 L); wire structs `crates/apub/objects/src/protocol/page.rs:Page` (:1–276); shared helpers `crates/apub/objects/src/utils/functions.rs` (:1–317 — `generate_to`, `verify_domains_match` wrappers, `read_from_id` chain, visibility verifiers).
**Signature:** pattern per type: `async fn to_apub(&self, context) -> Result<WireObject>`; `async fn from_apub(wire: WireObject, context) -> Result<DbRow>`; `async fn read_from_id(id: Url, context) -> Result<Option<Self>>` (fetch-or-DB).
**Data Shape:** `Page { id, actor?, attributedTo (Either<Url, PersonWithGroup{user, group}>), to/cc, kind: "Page", name (title), content (markdown/html), sensitive, attachment, language, ... }` with `#[serde(flatten)] extra: Map` catching unmapped keys; `attributedTo` is an EITHER because Lemmy emits the modern `{type: Person}{type: Group}` pair while accepting bare URLs from other software.

### Decisive source
```rust
// protocol structs tolerate the ecosystem: unknown fields land in `other`, required-vs-optional
// is decided by what OTHER servers actually emit, not by what lemmy would like
#[derive(Deserialize, Serialize, Debug)]
pub struct Page {
  pub id: Url,
  #[serde(rename = "type")] pub kind: PageType,
  #[serde(flatten)] pub other: HashMap<String, serde_json::Value>,  // lossless round-trip hook
  // r#type-style Either for attributedTo:
  pub attributed_to: Option<Either<Url, AttributedToPage>>,
  ...
}

// objects/post.rs — from_apub persists BOTH directions' truth:
// markdown source kept in `body`, generated HTML in `content`; remote URLs stored as-is
```

**Flow:** outbound: row → `to_apud`-style builder fills required AP fields + `generate_to(community)` + context header (`FEDERATION_CONTEXT`: join-lemmy.org context.json + activitystreams only — minimal-context bandwidth choice, `crates/utils/src/lib.rs:87–92`) → serialized into SentActivity. Inbound: fetch object by id (SSRF-guarded client) → deserialize into protocol struct (unknown keys preserved in `other`) → domain checks (`verify_domains_match(object.id, fetched url)`) → upsert DB row keeping local moderation columns untouched.
**Invariant:** wire structs are ECOSYSTEM-shaped, not DB-shaped: anything another server might legitimately send must deserialize (optional + flattened extras) or that server's content is silently dropped; DB rows keep BOTH raw text and rendered HTML so rendering choices stay local. Round-trip stability (parse → serialize equality on fixtures) is the compatibility contract.
**Probe:** fixture battery `crates/apub/apub/assets/{lemmy,mastodon,pleroma,friendica,gnusocial,mbin,discourse,...}/` (~14 software vendors) driven by `test_json::<T>(path)` / `test_parse_lemmy_item::<T>(path)` helpers (`crates/apub_objects/src/utils/test.rs`), e.g. `crates/apub/activities/src/activity_lists.rs:111–131`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "ApubPost", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-shape contract (DB model ≠ wire DTO), flatten-extra lossless deserialization, Either-typed polymorphic fields where the ecosystem disagrees, and a cross-vendor fixture corpus as the parse test suite. Adapt field names to your schema; KEEP the fixture-driven round-trip discipline. Omit markdown/HTML render pipeline specifics.
