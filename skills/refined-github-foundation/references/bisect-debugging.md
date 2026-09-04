<!-- capsule-v2 -->
# Interactive Feature Bisect — how do you let a user find which of 100+ toggles breaks their page, in log2 reloads?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the bisect state machine — where does the candidate list live, how are halves applied at boot, and how do multiple tabs stay honest?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/bisect.tsx:` `state` (:143), `bisectFeatures` (:231–279), `onChoiceButtonClick` (:188–229), `getMiddleStep` (:162); UI dialog (:169–185).
**Signature:** `bisectFeatures(): Promise<Record<string, boolean> | void>`; `startFeatureIdentification(origin?)` seeds `state`.
**Data Shape:** `CachedValue<FeatureId[]>('bisect', {maxAge: {minutes: 15}})` — cross-tab storage with TTL; value = remaining candidate feature ids.

### Decisive source
```ts
// Halve: yes = first half (suspects), no = second half
if (bisectedFeatures.length > 1) {
	await state.set(answer === 'yes'
		? bisectedFeatures.slice(0, getMiddleStep(bisectedFeatures))
		: bisectedFeatures.slice(getMiddleStep(bisectedFeatures)));
	location.reload();
	return;
}
```
```ts
// Boot-side application: candidates ENABLED only in the front half; everything else forced OFF
const half = getMiddleStep(bisectedFeatures);
for (const feature of importedFeatures) {
	const index = bisectedFeatures.indexOf(feature);
	temporaryOptions[`feature:${feature}`] = index !== -1 && index < half;
}
```

**Flow:** user triggers "identify feature" → full enabled list stored → every page load calls `bisectFeatures()`: if state exists it renders a Yes/No box ("Do you see the change or issue? (N steps remaining)", buttons disabled until window load) → answer splits the list and RELOADS → last step (single candidate) reports culprit or blames CSS/meta-features if even that one wasn't it → `state.delete()` ends the run. A `visibilitychange` listener shows "Process completed in another tab" if another window finished it.
**Invariant:** boot merges bisect options AFTER user options but BEFORE hotfixes lose priority — actually the precedence is explicit in feature-manager :128–136: **bisect wins over hotfix disables** (`if (bisectedFeatures) {Object.assign(options, bisectedFeatures)} else {...hotfix...}`). The 15-minute TTL bounds an abandoned session's blast radius. Steps = ceil(log2(n)) + 1 shown to set expectations.
**Probe:** no unit test (interactive); deterministic pins: split logic :192–201, temporary-options loop :270–275, precedence :128–136 of feature-manager.tsx. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "bisectFeatures startFeatureIdentification getMiddleStep", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any feature-flag-heavy client product as the support tool of last resort. Adapt storage medium (any cross-tab store) and dialog copy. Omit the multi-tab visibility UX at your peril — without it users run two halves concurrently. No direct test — caveat recorded.
