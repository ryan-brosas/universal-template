<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# LH Basis (Linked Helper v2.130.5 ingest): Domain-Kernel Foundation

## Use this for
Use when porting or re-deriving LinkedIn-automation domain machinery: multi-surface identity resolution (member ids vs profile hashes vs public ids), runtime type-guard layers over plain JS objects, message-template ASTs, action-payload shape validation, SQLite unique-collision detection through ORM error chains, or source-scoped entity schemas. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./external-identifier-type-algebra.md` — How do I validate and canonicalize a person identity that may arrive as 10 different wire types?
- `./hash-to-member-id-decoding.md` — How do I recover a stable numeric member id from an opaque profile hash?
- `./guard-kernel-composition.md` — How do I build a typed data model in plain JS without schema validators?
- `./message-template-node-tree.md` — How is a recursive template tree validated so bad branches cannot slip through?
- `./polymorphic-list-payload-guards.md` — How can one API accept entities, enrichment tuples, and batch tuples safely?
- `./cross-layer-error-collision-mining.md` — How do I detect a UNIQUE-constraint violation buried in ORM/driver error wrappers?
- `./source-scoped-domain-enums.md` — Where do platform taxonomies and conditional fields diverge per acquisition source?
- `./organization-external-identifier-guards.md` — How does a second identity family scale the identifier pattern down to two wire types?
- `./chat-message-external-identifiers.md` — What does validation look like for entities that never persist their own DB rows?
- `./person-aggregate-guard.md` — How do you duck-type a rich domain object by pinning BOTH its fields and its behavior?
- `./interval-and-limit-guards.md` — How are scheduling windows and metered action budgets validated?
- `./campaign-discriminator-guards.md` — How does an enum-discriminated aggregate split into People vs Organizations variants with presence AND absence sets?
- `./action-lifecycle-guards.md` — How is a family split enforced when the org variant has NO discriminator field?
- `./action-result-guards.md` — Why can an org variant's forbidden-key set differ completely from the other family's extra keys?
- `./postpone-reason-tagged-union.md` — How is a postponement reason typed across bare strings, limit references, and serialized errors?
- `./collection-object-guards.md` — What makes an object a valid Collection (the fourth action-payload shape)?
- `./search-payload-guards.md` — How are search-list requests and facet filters validated (and why so shallowly)?
- `./organization-aggregate-guard.md` — How does a smaller second aggregate reuse the duck-typing recipe without weakening it?
- `./message-aggregate-guards.md` — Which fields get type checks inside a whitelist guard, and what makes a pending entity behavior-bearing?
- `./action-config-dispatch-guard.md` — How does one validator cover every action type's config via enum membership plus nullable escape hatches?
- `./action-version-stats-projection.md` — How are Set-based operation stats folded into counts without double-reporting excluded people?
- `./dl-identifier-conversion.md` — How is an opaque id string classified into a typed identifier without throwing on garbage?
- `./organization-unique-id-normalization.md` — What changes when dedup-key normalization deliberately fails open instead of closed?
- `./scalar-taxonomy-guards.md` — How do you validate closed string vocabularies (statuses, tiers, categories) at runtime without TS enums?
- `./li-account-carrier-guard.md` — How do you validate a lightweight cross-system reference carrier that is NOT a DB row?
- `./pas-timestamp-ladder.md` — Which entity sync timestamps must exist as Date instances, and which one may be absent?
- `./person-type-group-projection.md` — How do you project identifier TYPE SETS onto groups with a fail-closed public entry over fail-open inner steps?
- `./base64url-codec-pair.md` — What does a base64url encode/decode pair hide about padding asymmetry?
- `./import-rejection-taxonomies.md` — How do you persist a CSV-import rejection code when the enum is 0-based AND its twin assigns different ordinals to the same name?
- `./week-working-schedule.md` — How is a weekly working calendar encoded so day keys, defaults, and minute bounds cannot drift?

## Capsule map
- **Identity type algebra** — `external-identifier-type-algebra`: 10 identifier types -> 4 groups (member|hash|public|avatar); group-dispatched validation; `${group}:${externalId}` canonical dedup key; auth-gated sn-/r-/t- variants carry authType/authToken.
- **Hash id decoding** — `hash-to-member-id-decoding`: base64url charset + length 39 + prefix ACo|ACw|AEE|AEM|AAE; memberId = readUInt32BE(4) of decoded blob; silent-null failure policy.
- **Guard kernel composition** — `guard-kernel-composition`: dbItem root guard (positive-number id) + object/string/date primitives composed bottom-up into entity guards; instanceof Date means in-process-only validation.
- **Template node tree** — `message-template-node-tree`: text/var/if/group/variants/variant recursive predicates; if-condition restricted to primitive groups.
- **List payload shapes** — `polymorphic-list-payload-guards`: four accepted payload shapes sharing one 4-slot suffix validator; collect deferrable as DBId.
- **Collision error mining** — `cross-layer-error-collision-mining`: cycle-safe recursive walk over data/cause/originalError/driverError matching code + externalIds.
- **Source-scoped schemas** — `source-scoped-domain-enums`: collectingScope legal only under source 'linkedin'; platform enum linkedin|salesNavigator|recruiter|talent; ActionTargetState includes Removed=-1.
- **Organization identifiers** — `organization-external-identifier-guards`: 2 types (public-id, company-id); company-id mirrors companyId:number; composite = dbItem ∧ data ∧ PAS dates; total serializer returns String(externalId) or null.
- **Chat/message identifiers** — `chat-message-external-identifiers`: chat = hash-id | internal-id (+ mirrored internalId:number), message = single public-id; DATA-level guards only — validation depth scales with persistence depth.
- **Person aggregate** — `person-aggregate-guard`: isIPerson = dbItem ∧ 37-property whitelist ∧ 45-method surface check; isPeople accepts IPerson OR bare DBId per element (deferrable references).
- **Intervals & limits** — `interval-and-limit-guards`: TInterval ordered numeric pair [start,end] with start<=end (point windows legal); ILimitType = dbItem ∧ type ∈ ALL_DEFAULT_LIMIT_TYPES (34 kinds) ∧ limits prop ∧ credit-method surface {getCreditsUsed, getCreditsWillBeAvailableDate, useCredits}.
- **Campaign discriminators** — `campaign-discriminator-guards`: CampaignType People=1|Organizations=2 positive split; org variant REQUIRES absence of replied/accepted/pendingReview; counter props mirror CampaignSubListTypes 1:1; method surface [setArchived,getInfo,getActionsInfo,validate].
- **Action lifecycle** — `action-lifecycle-guards`: NO discriminator field — family = presence vs REQUIRED ABSENCE of replied/messaged/pendingReview/actionLevelCustomFields over a versioned+iterated core (versions, currentIterationId, postponeReason).
- **Action results** — `action-result-guards`: shared (actionVersionId, actionIterationId, liAccountId, result, flags, targetPlatform) core; people +personId/messages; org +organizationId and forbids invitedPlatform/messagedPlatform — absence sets are per-family, never copy the sibling's.
- **Postpone reasons** — `postpone-reason-tagged-union`: six dataless reasons accept bare string OR {type}; LHLimit limitType is object|number|string; LinkedInLimit string-only; Error envelope pins whoToBlame ∈ [LinkedIn,Proxy,LH,User] + '[dump]' slot.
- **Collection objects** — `collection-object-guards`: dbItem ∧ {versions,name} ∧ methods {add,remove,clear,addWithStats,removeWithStats}; people/org guards byte-identical — same object passes both.
- **Search payloads** — `search-payload-guards`: search-list = non-array .request-holder; 'people'|'organizations' literal discriminators; facet option = {empty:bool}|{exists:bool}; in/nin key-presence array sets — transient payloads validate shallowly.
- **Organization aggregate** — `organization-aggregate-guard`: isIOrganization = dbItem ∧ 7-prop whitelist ∧ 7-method surface; recipe (dbItem∧props∧methods) family-invariant, only the lists scale (person 37/45 vs org 7/7); isOrganizations keeps per-element DBId deferral.
- **Message aggregates** — `message-aggregate-guards`: isIMessage types only 5 of 10 whitelisted props (subject string|null = nullable-but-required; relations presence-only); isIPendingMessage value-checks chatId as DBId and pins method surface {delete, setText} — pending entities are live objects.
- **Action config dispatch** — `action-config-dispatch-guard`: one any-type guard = actionType enum membership + common shape + two escape hatches (actionSettings null-or-object deferred, overridePlatform platform-or-null inherit).
- **Stats projection** — `action-version-stats-projection`: Set-based operation slots fold to {total:{...}} counts (.size not .length); addToQueue.successful reported NET of campaign+action exclude-list union with inExcludeList reclassification.
- **DL identifier conversion** — `dl-identifier-conversion`: narrow /^\d+$/ company branch before injectable wide public regex; at most ONE identifier; companyId mirror populated at construction; empty-array failure, never throw.
- **Org unique-id normalization** — `organization-unique-id-normalization`: TypeGroup.fromType returns unknowns UNCHANGED (fail-open) vs person's fail-closed dispatch; UniqueId.fromExternalId classifies a raw STRING → [0] → `${group}:${id}`, undefined on garbage.
- **Scalar taxonomies** — `scalar-taxonomy-guards`: closed literal arrays ARE the runtime vocabulary — taskStatuses ['unscheduled','scheduled','failed'], periodicTasksTypes ['collectSSIScores'], email 'personal'|'business', license 'pro'|'standard'; strict case-sensitive includes membership; guard lives next to its list.
- **LI-account carrier** — `li-account-carrier-guard`: isILiAccountIdData = truthy object + `liAccountId:number` ONLY — no dbItem, no id>0 (external account number, not rowid); negative passes (probe-observed).
- **PAS timestamp ladder** — `pas-timestamp-ladder`: createdAt/updatedAt/actualAt REQUIRED instanceof Date; sentAtToPAS optional (undefined|Date, wrong type falsifies); flat 4-way conjunction; ISO strings fail — in-process objects only.
- **Type→group projection** — `person-type-group-projection`: public fromType THROWS `Invalid types argument` on unknown singular OR any bad tuple element; private fromSingleType falls through open; tuple gate = non-empty array, every element Type|TypeGroup; Type.toGroup alias shares the throw.
- **Base64url codec pair** — `base64url-codec-pair`: decode re-pads `4 - len%4`, encode strips all '='; round-trip NOT symmetric for len%4===1 (over-pad observed) — gate decoding behind strict length/charset validation.
- **Import rejection taxonomies** — `import-rejection-taxonomies`: person vs campaign reason enums share NAMES at DIFFERENT ordinals (INVALID_CHECK_SUM = 3 vs 1); MISSING_QUOTES=0 is a VALID code, so falsiness corrupts records; both unguarded (porter adds membership checks).
- **Week working schedule** — `week-working-schedule`: DayOfWeek matches Date#getDay() (sunday=0..saturday=6); MinInDay/MinInWeek arithmetically derived; DEFAULT=all-working vs EMPTY=closed; integer-keyed maps enumerate ordinal-first regardless of insertion order.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Linked Helper v2.130.5 ingest (**proprietary commercial product — reuse citations-only, never vendor code**), non-Git curated checkout, pin `?@?`; Codebase Memory project `lh-basis` @ generation 2026-08-23T00:11:49Z (full mode, 1601 nodes / 2833 edges, 0 parse-partial / 0 skipped). Coverage caveat by design: core/local-source/dist, core/models/dist, core/launcher/dist are excluded subtrees — the engine, model dists, and launcher managers are NOT graph-addressable from this project.

## Full view (memory graph)
Revalidate `lh-basis` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record graph root, generation, node/edge counts, freshness, and coverage caveats; source decides shipped claims. No test runner exists in this extracted copy — deterministic node-require probes against real dist modules are the executable evidence (all 30 capsules probe-verified as of pass 14, 2026-08-26).

## Boundaries
Adopt pure guard/validation contracts, type-group dispatch, dedup-key normalization, error-chain mining, and payload-shape algebras. Adapt path/symbol names and enum values to your host schema. Omit all transport/product behavior (Electron launcher, CDP clients, proxy interception) and any secret-bearing package metadata; those parts are either outside the indexed surface or proprietary.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`action-config-dispatch-guard.md`](./action-config-dispatch-guard.md)
- [`action-lifecycle-guards.md`](./action-lifecycle-guards.md)
- [`action-result-guards.md`](./action-result-guards.md)
- [`action-version-stats-projection.md`](./action-version-stats-projection.md)
- [`base64url-codec-pair.md`](./base64url-codec-pair.md)
- [`campaign-discriminator-guards.md`](./campaign-discriminator-guards.md)
- [`chat-message-external-identifiers.md`](./chat-message-external-identifiers.md)
- [`collection-object-guards.md`](./collection-object-guards.md)
- [`cross-layer-error-collision-mining.md`](./cross-layer-error-collision-mining.md)
- [`dl-identifier-conversion.md`](./dl-identifier-conversion.md)
- [`external-identifier-type-algebra.md`](./external-identifier-type-algebra.md)
- [`guard-kernel-composition.md`](./guard-kernel-composition.md)
- [`hash-to-member-id-decoding.md`](./hash-to-member-id-decoding.md)
- [`import-rejection-taxonomies.md`](./import-rejection-taxonomies.md)
- [`interval-and-limit-guards.md`](./interval-and-limit-guards.md)
- [`li-account-carrier-guard.md`](./li-account-carrier-guard.md)
- [`message-aggregate-guards.md`](./message-aggregate-guards.md)
- [`message-template-node-tree.md`](./message-template-node-tree.md)
- [`organization-aggregate-guard.md`](./organization-aggregate-guard.md)
- [`organization-external-identifier-guards.md`](./organization-external-identifier-guards.md)
- [`organization-unique-id-normalization.md`](./organization-unique-id-normalization.md)
- [`pas-timestamp-ladder.md`](./pas-timestamp-ladder.md)
- [`person-aggregate-guard.md`](./person-aggregate-guard.md)
- [`person-type-group-projection.md`](./person-type-group-projection.md)
- [`polymorphic-list-payload-guards.md`](./polymorphic-list-payload-guards.md)
- [`postpone-reason-tagged-union.md`](./postpone-reason-tagged-union.md)
- [`scalar-taxonomy-guards.md`](./scalar-taxonomy-guards.md)
- [`search-payload-guards.md`](./search-payload-guards.md)
- [`source-scoped-domain-enums.md`](./source-scoped-domain-enums.md)
- [`week-working-schedule.md`](./week-working-schedule.md)
