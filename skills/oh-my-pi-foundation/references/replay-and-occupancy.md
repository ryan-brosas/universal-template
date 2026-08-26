<!-- capsule-v2 -->
# Replay and occupancy — native payloads need a portable escape hatch

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When can provider-native compacted history be replayed, and what happens after a provider switch?

## Reuse native data only for the active compatible provider
**Path/Symbol:** `packages/agent/src/compaction/compaction.ts:remotePreserveReusable` (1271–1282), `findReadableCompactionIndex` (1296–1308), `prepareCompaction` (1315+).
**Signature:** `remotePreserveReusable(preserveData, activeModel, settings): boolean`.
**Data Shape:** opaque preserve blob (V2 or OpenAI-remote) with provider, active model, remote-compaction settings.

### Decisive source
```ts
const remote = getCompactionV2PreserveData(preserveData) ?? getPreservedOpenAiRemoteCompactionData(preserveData);
if (!remote) return true;                                  // no native payload ⇒ portable history
if (settings.remoteEnabled === false) return false;
if (remote.provider !== activeModel.provider) return false; // provider switched ⇒ NOT reusable
const v2Ok = settings.remoteStreamingV2Enabled !== false && shouldUseCompactionV2Streaming(activeModel);
return v2Ok || shouldUseOpenAiRemoteCompaction(activeModel);
```

**Flow:** locate the newest compaction entry → compare its preserved provider to the ACTIVE model, not a candidate role model → reuse only when decodable + settings-allowed → otherwise `prepareCompaction` re-expands originals past it for a portable local summary. The doc comment pins the rule: an unreadable entry "summarizes nothing" — maintenance ops must not skip entries no summary covers.

**Invariant:** a provider-switched session never keeps an opaque placeholder as its only recoverable history.

**Probe:** direct `packages/agent/test/remote-compaction.test.ts:309–415` tracks native call IDs and drops stale outputs after a full-snapshot payload.

## Occupancy is the larger trustworthy signal
**Path/Symbol:** `compaction.ts:compactionContextTokens` (358), `prepareCompaction`.
**Signature:** `compactionContextTokens(providerContextTokens, storedConversationEstimate): number`.
**Data Shape:** provider usage is wire-shaped (last response); stored estimate is durable replay-shaped.
**Flow:** clamp both to valid counts → choose the LARGER → evaluate the compaction threshold against that.
**Invariant:** reduced wire usage cannot hide stored history that still exceeds a usable context window.
**Probe:** direct `compaction-reserve-provenance.test.ts:13–92` exercises explicit/default reserve provenance; add a target-specific transformed-wire occupancy case when porting. Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "remotePreserveReusable findReadableCompactionIndex replay", limit: 8, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.agent.src.compaction.compaction.remotePreserveReusable" });
```

## Verdict
Adopt provider-compatibility gating of opaque payloads with re-expand-on-mismatch, and max(wire, stored) occupancy for thresholds; adapt preserve-blob schemas and model checks to host providers; omit OpenAI/V2-specific toggles unless targeting those transports.
