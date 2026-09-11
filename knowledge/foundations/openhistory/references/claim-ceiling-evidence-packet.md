<!-- capsule-v2 -->
# Claim-ceiling evidence packet — how do you convert raw telemetry into LLM instructions that cannot overstate what happened?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** How should event evidence be grouped, ranked, and phrased so a summarizer never claims an outcome stronger than the observations prove?

## buildEpisodeEvidencePacket
**Path/Symbol:** `src/main/episode-evidence.ts:buildEpisodeEvidencePacket` (lines 42-179), `evidenceStrength` (243-247), `addContentChange` (374-405).
**Signature:** `buildEpisodeEvidencePacket(episode: ActivityEpisode): EpisodeEvidencePacket`; renderers `renderEpisodeEvidenceBrief` (181-204) / `renderCompactEpisodeEvidenceBrief` (206-241).
**Data Shape:** packet = `{calibration{durationSeconds, mode: context_only|sparse_literal|standard, counts}, workUnits[], evidenceBoundaries[], ambientContext[]}`; each unit carries `claimCeiling: demonstrated_result > submitted_action > draft_or_revision > literal_interaction > navigation_only`, `materiality`, `safeLeadVerbs`.

### Decisive source
```ts
const key = JSON.stringify([application ?? "", durableObject ?? ""]);   // group per app + durable object
...
unit.priorityScore += 80 + Math.min(deleted, 1_000) / 5 + Math.min(resultingValue.length, 2_000) / 20; // drafts
if (/\b(send|submit|publish|post)\b/i.test(interaction)) { ... unit.priorityScore += 120; }            // submissions
if (outcome) { pushUnique(unit.demonstratedOutcomes, outcome.description, 3); unit.priorityScore += 1_000; }
const claimCeiling = unit.demonstratedOutcomes.length ? "demonstrated_result"
  : unit.submissionActions.length ? "submitted_action"
  : unit.contentChanges.length ? "draft_or_revision"
  : unit.interactions.length ? "literal_interaction" : "navigation_only";
```

**Flow:** classify each event (direct_action / navigation / context / boundary) → context events become capped ambient strings only → direct/navigation events accumulate into work units keyed by (application, durable object) with additive priority weights (+80 base draft scaled by edit size, +120 explicit send/submit/publish/post click, +1000 explicitly displayed success) → units ranked by score and assigned the highest claim their evidence supports plus safe lead verbs → `addContentChange` supersedes earlier "Final observed edited text" snapshots by quoted-payload containment (later state replaces stale prefixes) → renderers emit instructions whose title verbs are bounded by the claim ceiling, with anti-overstatement boundary sentences ("clicking Send supports the user-initiated submission action, but not downstream delivery, processing, or success").
**Invariant:** no absolute timestamps ever reach the brief (test-pinned); a control label is interaction evidence, never an outcome; address-bar input is a query (`literal_interaction`), not drafted work; empty-evidence episodes force "Displayed"-only language.
**Probe:** `src/main/episode-evidence.test.ts` — executed GREEN at pin in the combined run ("tests 31, pass 30"): submission grouping + `safeLeadVerbs ["Sent"]` (:10-49), final-snapshot supersede + static-text non-promotion (:51-89), ranking demonstrated_result > draft > literal (:105-155), address-bar query grammar (:202-228), consequential-later-draft retention (:230-254).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "buildEpisodeEvidencePacket claimCeiling workUnits", limit: 10 });
```
Executed live byte-for-byte: top rows are `buildEpisodeEvidencePacket`, `renderEpisodeEvidenceBrief`, `renderCompactEpisodeEvidenceBrief` in `episode-evidence.ts`; no unrelated subsystem above them.

## Verdict
Adopt the claim-ceiling ladder, additive evidence weighting for ranking, snapshot-supersede content tracking, and machine-readable anti-hallucination boundaries fed to the model; adapt the regex vocabularies (send verbs, success phrases) and weights to your domain; omit Apple accessibility role normalization. Coverage: `no_recorded_issue` on `src/main/episode-evidence.ts`; probe suite executed green at pin.
