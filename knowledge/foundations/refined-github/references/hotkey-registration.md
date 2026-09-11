<!-- capsule-v2 -->
# Hotkeys via Hidden Elements — how do you add keyboard shortcuts that survive SPA navigation without global key listeners?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the delegation mechanism behind `registerHotkey`, and what is the shortcut-registry side effect?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/hotkey.tsx:` `registerHotkey` (:333–347 of combined listing), `addHotkey` (:350–358), `modifierKey` (:360); registry `source/helpers/feature-helpers.ts:shortcutMap` (:1).
**Signature:** `registerHotkey(hotkey: string, functionOrUrl: MouseEventHandler<HTMLButtonElement> | string, {signal}?): void`; `addHotkey(button, hotkey: string): void`.
**Data Shape:** hidden `<a href>` (URL variant) or hidden `<button onClick>` prepended to body carrying `data-hotkey="<combo>"` — GitHub's own hotkey delegation does the rest.

### Decisive source
```ts
const element = typeof functionOrUrl === 'string'
	? <a hidden href={functionOrUrl} data-hotkey={hotkey} />
	: <button hidden type="button" data-hotkey={hotkey} onClick={functionOrUrl} />;
document.body.prepend(element);
signal?.addEventListener('abort', () => { element.remove(); });
```
```ts
// Merge multiple shortcuts onto ONE element without losing existing ones:
const hotkeys = new Set(button.dataset.hotkey?.split(','));
hotkeys.add(hotkey);
button.dataset.hotkey = [...hotkeys].join(',');
```

**Flow:** feature init calls registerHotkey → hidden element becomes the hotkey target until its AbortSignal removes it (per-run teardown matches the feature lifecycle) → successful runs also record `shortcutMap.set(hotkey, description)` from the loader's `shortcuts` option so the help dialog can list RGH-added keys.
**Invariant:** registration is DOM-presence-based — removing the element IS the unregister; there is no listener bookkeeping. `addHotkey` must go through Set-dedup because GitHub's `data-hotkey` accepts comma-separated combos and blind concatenation duplicates them on re-runs. Platform modifier: `modifierKey = isMac ? 'cmd' : 'ctrl'`.
**Probe:** `source/github-helpers/hotkeys.test.ts` pins shortcut-string parsing used by the help-screen aggregation (`shortcutMap` consumer); registration itself is browser-bound (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "registerHotkey addHotkey shortcutMap data-hotkey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when extending a host that already owns a `data-hotkey` delegator; otherwise adapt by shipping your own delegated keydown handler keyed on the same dataset attribute. Omit the help-dialog map if you have no shortcut UI. Partial test coverage — caveat recorded.
