<!-- capsule-v2 -->
# Airtable AI-field upgrade — how does an aiText column become a live AI field only when the deployment can serve it?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How is the Airtable aiText prompt normalized, rebuilt with remapped field references, and what gates the upgrade vs snapshot fallback?

## applyAiConfig + resolveAiModelKey
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` — `resolveAiModelKey` (:488–495), `applyAiConfig` (:502–544); planner side `normalizeAiPromptParts` in `airtable-schema-mapper.ts` (:292–312).
**Signature:** `private applyAiConfig(planned: IPlannedDirectField, aiModelKey: string | undefined, fieldIdMap, tableName, issues): IFieldRo`.
**Data Shape:** prompt parts = `[{text}] | [{airtableFieldId, fieldName}]`; model key from base AI config (`config.chatModel?.lg`) resolved once per import; degradation issue carries `toType: 'longText snapshot'`.

### Decisive source
```ts
const prompt = planned.aiPromptParts
  .map((part) => {
    if (part.text != null) return part.text;
    const teableFieldId = part.airtableFieldId && fieldIdMap[part.airtableFieldId];
    if (teableFieldId) return `{${teableFieldId}}`;
    return part.fieldName ?? '';
  })
  .join('');
if (!aiModelKey || !prompt.trim()) {
  issues.push({ code: 'fieldDegraded', ..., toType: 'longText snapshot',
    reason: aiModelKey ? 'the AI prompt is empty' : 'no AI model is configured' });
  return planned.ro;   // keep the imported text values as plain LongText
}
return { ...planned.ro,
  aiConfig: { type: FieldAIActionType.Customization, modelKey: aiModelKey, prompt,
    // Keep imported snapshot values; users can enable auto-fill later to
    // avoid triggering a generation for every imported record.
    isAutoFill: false } };
```

**Flow:** planner normalizes Airtable's prompt array (text chunks + field-ref objects, both shapes `{field:{fieldId}}` and bare `fieldId`) into typed parts carrying the source field NAME for fallback → at table creation each aiText field rebuilds its prompt by remapping part field ids through fieldIdMap (unmapped refs degrade to the readable name) → model key resolution failure or empty prompt ⇒ keep the LongText snapshot of imported values and report.
**Invariant:** The AI field is created WITH the imported snapshot and `isAutoFill:false` — importing never triggers a paid generation per record; users opt into auto-fill later. Model-key lookup failure is swallowed (`resolveAiModelKey` catches everything) so AI-config absence can never fail an import.
**Probe:** Direct tests: `airtable-import.service.spec.ts` it('builds a customization AI config with mapped field references') :48, it('keeps the snapshot and reports when no AI model is configured') :66; `airtable-schema-mapper.spec.ts` it('carries a normalized AI prompt for aiText fields without degrading them upfront') :273.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"applyAiConfig normalizeAiPromptParts resolveAiModelKey","limit":5,"detail":"ids"}'
```

## Verdict
Adopt normalize→remap→gate-with-snapshot-fallback for any LLM-field import; adapt config keys; omit teable's FieldAIActionType enum. Coverage caveat: none.
