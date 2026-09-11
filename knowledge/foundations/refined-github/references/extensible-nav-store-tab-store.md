<!-- capsule-v2 -->
# extensible-nav-store-tab-store — how do several independent features contribute tabs to one host nav bar without owning the DOM?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How can N features each add/rename/demote/select tabs in a single SPA navigation bar, with no shared DOM ownership and safe replacement of the native list?

## Three-store merge: native + extra + override
**Path/Symbol:** `source/components/extensible-nav-store.ts` — stores :22–26, derived `tabs` :28–43, `setNativeTabs` :45–47, `selectTab` :49–51, `addTab` :53–64, `overrideTab` :66–68, `updateCurrentTab` :70–81 (whole file 81 lines).
**Signature:** `setNativeTabs(list: Tab[]): void`; `addTab(tab: Tab, before?: string): void`; `overrideTab(id: string, override: Partial<Pick<Tab, 'label'|'counter'|'tooltip'|'demoted'|'removed'>>): void`; `updateCurrentTab(): Promise<void>`; exports `tabs: Readable<Tab[]>`, `selectedId: Readable<string|undefined>`.
**Data Shape:** `Tab = {id, href, label, icon, reactNav?, counter?: Readable<number|string|undefined>, tooltip?, demoted?: true|string (user-visible reason), removed?: true (only when known 404), selected?: () => boolean|Promise<boolean>}`. `extraTabs` items are `{tab, before?}`; `overrides` is a `Map<string, TabOverride>`.

### Decisive source
```ts
export const tabs = derived(
	[nativeTabs, extraTabs, overrides],
	([$nativeTabs, $extraTabs, $overrides]) => {
		const tabs = $nativeTabs.map(tab => ({...tab, ...$overrides.get(tab.id)}));
		for (const {tab, before} of $extraTabs) {
			const index = before ? tabs.findIndex(({id}) => id === before) : -1;
			tabs.splice(index === -1 ? tabs.length : index, 0, tab);
		}
		const demoted = tabs.filter(tab => tab.demoted);
		const rest = tabs.filter(tab => !tab.demoted);
		return [...rest, ...demoted];
	},
);
// updateCurrentTab:
for (const {tab} of get(extraTabs)) {
	// eslint-disable-next-line no-await-in-loop -- Tabs must be tried in order, first match wins
	if (await tab.selected?.()) { selectTab(tab.id); return; }
}
const currentTab = $('nav[aria-label="Repository"] a[aria-current][data-tab-item]');
selectTab(currentTab.getAttribute('data-tab-item')!);
```

**Flow:** host nav parsed once → `setNativeTabs(items.map(generateTab))` + `selectTab(current)` → each contributing feature calls `addTab`/`overrideTab` at its own pace → the derived store re-merges on ANY of the three writables changing → Svelte view (`extensible-nav.svelte`) renders `$tabs` keyed by `tab.id`. Selection refresh: `updateCurrentTab()` awaits extra tabs' `selected()` predicates one by one (first true wins), else reads the host DOM's `aria-current`.
**Invariant:** (1) native-list replacement NEVER drops extras or overrides — they live in separate stores and the merge recomputes; (2) demotion is a STABLE partition (`[...rest, ...demoted]` preserves relative order inside both groups); (3) `before` anchor that matches nothing appends to the end (findIndex −1 → splice at length) — never throws; (4) `updateCurrentTab` must stay sequential — parallelizing the `selected()` checks breaks first-match-wins ordering; (5) the stores are MODULE SINGLETONS — all features share one instance, and tests must `vi.resetModules()` + dynamic re-import per case.
**Probe:** DIRECT TEST `source/components/extensible-nav-store.test.ts` (11 cases, whole file read): starts empty; reflects native tabs; append without `before`; insert before matching id; unknown `before` appends; multiple extras before same anchor keep call order (`['code','bugs','triage','issues']`); label override; two overrides MERGE (`{label:'AI agents', demoted:true}`); demoted natives move to end preserving order; **replacing native tabs does not drop extra tabs**; selectedId tracking. Executed pins: `grep -n "TODO|no-await-in-loop|nav\[aria-label" source/components/extensible-nav-store.ts` → lines 56, 72, 79.
**Consumer evidence:** live `search_code "extensible-nav-store"` → 5 features + svelte view: `extensible-nav.tsx` (setNativeTabs/selectTab/updateCurrentTab), `bugs-tab.tsx:92` + `releases-tab.tsx:58` (addTab with async `selected`), `new-repo-disable-projects-and-wikis.tsx:27-28` (overrideTab removed:true). Dual registration in `extensible-nav.tsx:106-114`: same URL registered twice — `init: onetime(initOnce)` (setup exactly once) plus `init: updateCurrentTab` (re-run every soft navigation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", qn_pattern: "components.extensible-nav-store.*", limit: 40 });
// total: 20 → Tab/ExtraTab/TabOverride types, 5 fns, 4 stores, test module (loadModule/makeTab/icon)
```
Executed 2026-08-27 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the three-store merge as the standard shape for multi-contributor UI registries (tabs, menu sections, status chips): independent writables + one derived merge means contributors can never clobber each other, and "replace the base list" is always safe. Adopt the dual-registration idiom (one-time setup init + per-navigation refresh init under the same feature URL) for any store-backed overlay. Adapt the `Tab` fields (icon component type, `reactNav`, counter store) to your host's nav model; omit the GitHub-specific fallback selector (`nav[aria-label="Repository"]`) and the octicon map. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; direct test exists and was read in full — strongest evidence class in this leaf.
