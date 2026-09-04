<!-- capsule-v2 -->
# Bulk paste parser — how do you import 50 prompts and account for every line?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should a bulk importer report what it dropped so users don't count?

## Every skipped line gets a reason bucket
**Path/Symbol:** `packages/lib/src/bulk-prompts.ts:SkippedLines` (L10–19), `parseBulkPrompts` (L57–104), `describeSkipped` (L112+).
**Signature:** `parseBulkPrompts(text, {existing?, limit? = MAX_PROMPTS}): { added: string[], skipped: { blank, duplicateOfExisting[], duplicateInPaste[], overCapacity[] } }`.
**Data Shape:** dedupe key = `trim → collapse internal whitespace → lowercase` (a line re-pasted from a wrapped document isn't a second prompt). Capacity measured against the WHOLE list: `room = max(0, limit − existing.length)`.

### Decisive source
```ts
// Capacity is checked after the duplicate rules on purpose. A line that was
// never going to be added is not competing for a slot, so reporting it as over
// capacity would blame the limit for something the limit did not cause.
if (added.length >= room) { skipped.overCapacity.push(value); continue; }
```
Order of checks per line: blank → duplicate-in-paste → duplicate-of-existing → over-capacity.

**Flow:** in-paste set fills only with ADDED lines (duplicates-of-existing don't poison it); `describeSkipped` renders one human sentence for duplicates/blanks but deliberately omits over-capacity lines — those BLOCK the paste as an error instead ("they block the paste outright rather than being skipped").
**Invariant:** "pasting fifty lines and getting forty-one prompts with no explanation is the case this parser exists to avoid, since the nine that vanished are indistinguishable from a bug." Check order is part of the contract — attribution of blame to the right rule.
**Probe:** `packages/lib/src/bulk-prompts.test.ts` (GREEN in probe run; bucket + ordering cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "parseBulkPrompts describeSkipped dedupeKey SkippedLines", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reason-bucket shape and check order wholesale; adapt MAX limit; omit nothing — this generalizes to any bulk-import UX.
