<!-- capsule-v2 -->
# storage-byte-accounting-polyfill — how do you measure extension storage usage when the native API exists but throws?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** `chrome.storage.getBytesInUse()` is the native way to report quota usage, but on Safari iOS the method EXISTS yet throws when called. How do you report honest byte counts across all browsers?

## Native-first ladder with a serialization polyfill
**Path/Symbol:** `source/helpers/used-storage.ts` — `getTrueSizeOfObject` :1–8, `getStorageBytesInUse` :11–18, `getStoredItemSize` :20–23, `hasUsedStorage` :25–30 (whole file 30 lines).
**Signature:** `getTrueSizeOfObject(object: Record<string, any>): number`; `getStorageBytesInUse(area: 'local' | 'sync'): Promise<any>`; `getStoredItemSize(area: chrome.storage.AreaName, item: string): Promise<number>`; `hasUsedStorage(): Promise<boolean>`.
**Data Shape:** all functions return UTF-8 byte counts (numbers); the polyfill counts over the FULL serialized area or a single item.

### Decisive source
```ts
export function getTrueSizeOfObject(object: Record<string, any>): number {
	// Firefox https://bugzilla.mozilla.org/show_bug.cgi?id=1385832#c20
	return new TextEncoder().encode(
		Object.entries(object)
			.map(([key, value]) => key + JSON.stringify(value))
			.join(''),
	).length;
}

/** `getBytesInUse` polyfill */
export async function getStorageBytesInUse(area: 'local' | 'sync'): Promise<any> {
	const storage = chrome.storage[area];
	try {
		return await storage.getBytesInUse(); // Exists in Safari iOS, but can't be called...
	} catch {
		return getTrueSizeOfObject(await storage.get());
	}
}
```

**Flow:** try the NATIVE `getBytesInUse()` first → on throw, fall back to counting UTF-8 bytes of every `key + JSON.stringify(value)` concatenated (TextEncoder — the Firefox bug link documents why string `.length` is wrong for non-Latin content) → `getStoredItemSize` skips the native attempt entirely because there is no per-item native API — it always runs the polyfill over `storage.get(item)` → `hasUsedStorage` ORs sync>0 and local>0.
**Invariant:** (1) native-first ordering matters: where the native API works it reports REAL engine-level usage (including overhead the polyfill cannot see); the polyfill is only the degraded path; (2) the catch is BARE (`catch {`) — any failure mode of the native call degrades, not just a specific error; (3) the polyfill counts `key + JSON.stringify(value)` per entry (keys included, no separators) — it is an ESTIMATE by construction, and ports must not present it as exact; (4) `hasUsedStorage` is DEAD CODE in this pin — exported with zero consumers repo-wide (graph trace callers_total 0 + whole-repo grep agree); cited as evidence of the intended surface, not a live path.
**Probe:** no direct unit test (chrome.storage-bound). Executed pins: `grep -n "TextEncoder" source/helpers/used-storage.ts` → line 3; `grep -n "getBytesInUse" source/helpers/used-storage.ts` → lines 14, 16; `grep -n "catch" source/helpers/used-storage.ts` → line 15. Live `trace_path inbound getStorageBytesInUse` → callers_total 1 (hasUsedStorage); `trace_path inbound getTrueSizeOfObject` → callers_total 3 (all inside used-storage.ts).

## Consumer: quota display with a low-space warning invariant
**Path/Symbol:** `source/options/storage-usage.svelte` — script :1–54, output :56–62 (whole file 62 lines).
**Signature:** Svelte 5 component, `$props(): {area: 'sync' | 'local'; item?: string}`.

### Decisive source
```svelte
	const available = $derived.by(() => {
		const storage = chrome.storage[area];
		return (item
			? (storage as chrome.storage.SyncStorageArea).QUOTA_BYTES_PER_ITEM
				?? storage.QUOTA_BYTES
			: storage.QUOTA_BYTES) - used;
	});
	// …onChanged handler:
	if (item && Object.hasOwn(changes, item)) {
		used = getTrueSizeOfObject(changes[item].newValue);
	}
	if (areaName === area) {
		getStorageUsage();
	}
```
```svelte
	{
		available < 100_000
			? `Only ${prettyBytes(available)} available`
			: `${prettyBytes(used)} used`
	}
```

**Flow:** measure on mount ($effect) → subscribe to `chrome.storage.onChanged` (listener removed on unmount) → for ITEM mode, a change to that item short-circuits to a SYNCHRONOUS `getTrueSizeOfObject(changes[item].newValue)` (no async round-trip needed — the new value is right there) while any same-area change still triggers a full re-measure → available = quota − used, where item mode uses `QUOTA_BYTES_PER_ITEM ?? QUOTA_BYTES` (the per-item constant only exists on sync areas — hence the cast) → display flips to a WARNING ("Only X available") below 100 KB free, otherwise shows "X used".
**Invariant:** (1) the 100 KB threshold is the display contract — below it the message changes from informational to warning; (2) the per-item fast path must use the CHANGE's newValue (the store already reflects it) — re-reading via get() would race the change event; (3) the `?? QUOTA_BYTES` fallback keeps local-area item views working where QUOTA_BYTES_PER_ITEM is undefined.
**Probe:** no direct unit test (Svelte/chrome-bound). Executed pins: `grep -n "QUOTA_BYTES_PER_ITEM" source/options/storage-usage.svelte` → line 20; `grep -n "100_000" source/options/storage-usage.svelte` → line 58; `grep -n "getTrueSizeOfObject(changes" source/options/storage-usage.svelte` → line 37. COVERAGE CAVEAT: this file is parse_partial (lines 1–55 flagged in index_status) — graph nodes may be missing; ALL claims above come from the direct source read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getStorageBytesInUse getTrueSizeOfObject getStoredItemSize hasUsedStorage", mode: "ids" });
// total: 4, all in source/helpers/used-storage.ts, line-exact (1-8 / 11-18 / 20-23 / 25-30)
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "getStorageBytesInUse", direction: "inbound" });
// callers_total: 1 (hasUsedStorage) — the svelte consumer is invisible to the graph (parse_partial)
```
Executed 2026-08-28 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the native-first/catch-fallback ladder and the TextEncoder entry-concatenation byte estimate — they are browser-agnostic degradation mechanics for any platform API that exists-but-throws on some engines. Adapt the 100 KB warning threshold, the quota constants, and the display copy to your host's quotas. Omit `hasUsedStorage` (dead code at this pin) unless your port needs the sync+local OR check. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on both paths; storage-usage.svelte is parse_partial (1–55) — source-read citation; no upstream direct tests (chrome-bound) — deterministic source pins stand in. Cross-reference: options-rename-migrations.md (the options-storage plane this display reads from).
