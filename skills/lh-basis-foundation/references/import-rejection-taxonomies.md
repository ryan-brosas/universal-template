<!-- capsule-v2 -->
# Import rejection taxonomies — How do you persist a CSV-import rejection code when the enum is 0-based AND its twin assigns different ordinals to the same name?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ gen 2026-08-23T00:11:49Z. **Question:** when an imported CSV row is rejected, what does the persisted reason code actually mean — and which naive encodings corrupt the record?

## Two same-purpose reason enums that are NOT interchangeable
**Path/Symbol:** `core/public-methods/shared-types/importData/enums.js` — `UnprocessedCSVPersonReason` (6–14), `UnprocessedCSVCampaignReason` (15–22).
**Signature:** exported reverse-keyed TS enum namespaces; member access yields `number`, reverse map yields `string`. NO membership guard exists anywhere in this module.
**Data Shape:** person reasons `0..5` (MISSING_QUOTES, PROFILE_NOT_FOUND, DIFFERENT_LINKEDIN_AND_PROFILE_URL_IDS, INVALID_CHECK_SUM, EMPTY_EXTERNAL_IDS, FAILED_TO_CREATE_PROFILE); campaign reasons `0..4` (MISSING_QUOTES, INVALID_CHECK_SUM, INVALID_ACTION_TYPE, INVALID_ACTION_SETTINGS, FAILED_TO_CREATE_CAMPAIGN).

### Decisive source
```js
var UnprocessedCSVPersonReason;
(function (UnprocessedCSVPersonReason) {
    UnprocessedCSVPersonReason[UnprocessedCSVPersonReason["MISSING_QUOTES"] = 0] = "MISSING_QUOTES";
    UnprocessedCSVPersonReason["PROFILE_NOT_FOUND"] = 1;
    UnprocessedCSVPersonReason["DIFFERENT_LINKEDIN_AND_PROFILE_URL_IDS"] = 2;
    UnprocessedCSVPersonReason["INVALID_CHECK_SUM"] = 3;
    UnprocessedCSVPersonReason["EMPTY_EXTERNAL_IDS"] = 4;
    UnprocessedCSVPersonReason["FAILED_TO_CREATE_PROFILE"] = 5;
})(...);
var UnprocessedCSVCampaignReason;
(function (UnprocessedCSVCampaignReason) {
    UnprocessedCSVCampaignReason[UnprocessedCSVCampaignReason["MISSING_QUOTES"] = 0] = "MISSING_QUOTES";
    UnprocessedCSVCampaignReason["INVALID_CHECK_SUM"] = 1;
    UnprocessedCSVCampaignReason["INVALID_ACTION_TYPE"] = 2;
    UnprocessedCSVCampaignReason["INVALID_ACTION_SETTINGS"] = 3;
    UnprocessedCSVCampaignReason["FAILED_TO_CREATE_CAMPAIGN"] = 4;
})(...);
```

**Flow:** the importer validates each CSV row against its family's pipeline; on failure it stamps the row with the FAMILY-SPECIFIC numeric reason and persists it. Person reasons encode identity-kernel failure modes: `DIFFERENT_LINKEDIN_AND_PROFILE_URL_IDS` is the denormalized-mirror invariant failing at import time (the same invariant `external-identifier-type-algebra` enforces via `memberId === Number(externalId)`), `INVALID_CHECK_SUM` is the profile-hash checksum gate, `EMPTY_EXTERNAL_IDS` is identifier-family emptiness. Campaign reasons instead name config-pipeline failures (action type / settings).
**Invariant — the positional traps:**
1. **Zero is a valid code.** `MISSING_QUOTES = 0` in BOTH enums; any falsiness test (`if (reason)`) treats a real rejection as "no reason". Test `=== undefined` or reverse-map membership instead.
2. **Same names, different ordinals.** `INVALID_CHECK_SUM` is `3` for persons but `1` for campaigns. Codes are meaningless outside their family enum; never merge the two vocabularies into one lookup table or log translation.
3. **Unguarded.** Neither enum has a runtime membership predicate; a bad lookup returns `undefined` silently (probe below). A porter must ADD the validation this kernel omits.

**Probe (executed pass 14, deterministic node-require against shipped dist module):**
```bash
node -e "const e=require('/mnt/hdd/utopia/inspo/lh-basis/core/public-methods/shared-types/importData/enums.js');const p=e.UnprocessedCSVPersonReason,c=e.UnprocessedCSVCampaignReason;console.log(p.INVALID_CHECK_SUM,c.INVALID_CHECK_SUM,p.MISSING_QUOTES,Boolean(p.MISSING_QUOTES),p[3])"
```
→ observed `3 1 0 false INVALID_CHECK_SUM` (ordinal split live; MISSING_QUOTES falsy; reverse map resolves 3 → INVALID_CHECK_SUM).

## Get live surrounding code
**Retrieve (executed pass 14):**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", name_pattern: "^UnprocessedCSV.*" });
```
→ observed exactly 2 rows ranking both enums (`enums.js` 15-15 campaign, 6-6 person). Retrieval caveat: BM25 `query:` search filters out Variable nodes — anchored prefix `name_pattern` forms are the reliable route for vocabulary seams.

## Verdict
Adopt: per-family rejection-code enums whose member sets mirror what each import pipeline can actually fail on; persist codes with explicit `undefined` checks and translate through the family's own enum only. Adapt: add the missing membership guards and prefer string codes if your store is debug-facing. Omit: the LinkedIn-specific failure semantics behind PROFILE_NOT_FOUND/checksum (engine side, unindexed). Coverage: `core/public-methods/shared-types/importData/enums.js` fully indexed (`no_recorded_issue` @ gen 2026-08-23T00:11:49Z); no test runner in ingest — deterministic probe evidence above. Corrects this leaf's earlier blanket claim that `importData/` was an empty type-only shell: the BARREL is empty, `enums.js` is not.

Cross-references: scalar-taxonomy-guards (guarded-literal-array style vs these unguarded ordinal enums); external-identifier-type-algebra (the mirror invariant whose import-time failure DIFFERENT_LINKEDIN_AND_PROFILE_URL_IDS names).
