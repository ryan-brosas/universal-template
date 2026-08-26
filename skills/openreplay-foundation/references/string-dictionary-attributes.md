<!-- capsule-v2 -->
# AttributeSender StringDictionary — when do you dictionary-encode attribute names/values on the wire?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How are repeated attribute strings compressed into numeric ids without desyncing player and recorder?

## Time-derived ids + explicit first-send
**Path/Symbol:** `tracker/tracker/src/main/modules/attributeSender.ts` — `StringDictionary.getKey` (:16–35), `AttributeSender.sendSetAttribute` (:48–61), `applyDict` (:63–69); disabled path `App.options.disableStringDict || crossdomain.enabled` (`app/index.ts:355–358`).
**Signature:** `getKey(str: string): [id: number, isNew: boolean]`; `applyDict(str): number`.
**Data Shape:** id = `Date.now() % 10^11`, collision suffix `id*10000 + lastSuffix++` while the shaved ms is unchanged; message pair `StringDictGlobal(id, str)` then `SetNodeAttributeDictGlobal(id, nameId, valueId)`.

### Decisive source
```ts
const safeKey = `__${str}`            // avoid native object props
if (!this.backDict[safeKey]) {
  isNew = true
  const shavedTs = Date.now() % 10 ** (13 - 2)   // shave century digits
  let id = shavedTs
  if (id === this.lastTs) { id = id * 10000 + this.lastSuffix++ } else { this.lastSuffix = 1 }
  this.backDict[safeKey] = id
}
return [this.backDict[safeKey], isNew]
```

**Flow:** sendSetAttribute → if dict enabled, map name & value through getKey → new strings emit a StringDictGlobal definition BEFORE the attribute message that references them; `clear()` swaps in a fresh dictionary at session stop so ids never leak across sessions.
**Invariant:** Definition-before-reference ordering is mandatory (player must resolve before applying). Dict must be disabled for cross-domain frames (separate dictionaries would collide) — enforced by constructor flag.
**Probe:** `grep -c 'shaving the first 2 digits' tracker/tracker/src/main/modules/attributeSender.ts` → `1`; `grep -c '__${str}' tracker/tracker/src/main/modules/attributeSender.ts` → `1`; direct tests `tests/StringDictionary.unit.test.ts` + `tests/attributeSender.test.ts::should send the string dictionary entry if the attribute is new` (executed green).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "StringDictionary getKey applyDict SetNodeAttributeDictGlobal", limit: 10 });
```

## Verdict
Adopt definition-before-reference dict encoding. Adapt id derivation (timestamp shave is quirky but monotone-enough). Omit for low-attribute targets.
