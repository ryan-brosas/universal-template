<!-- capsule-v2 -->
# Watch filename filter null-passthrough — how do you filter fs events without losing un-named ones?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** Some platforms deliver fs events with a null filename — does a filtered watch automation miss them?

## Filename-matching gate that lets null through
**Path/Symbol:** `packages/server/src/folder-watch-manager.ts:onFsEvent` (:134–159).
**Signature:** `(automationId, _event, filename: string | null): void`.
**Data Shape:** Filter = user glob string compiled per-event via `picomatch(filter)` (brace expansion supported); `_event` ("rename"/"change") deliberately ignored.

### Decisive source
```ts
if (
      automation?.trigger.kind === "watch" &&
      automation.trigger.filter &&
      filename !== null &&
      !picomatch(automation.trigger.filter)(filename)
    ) {
      return;
    }
```

**Flow:** fs event → grace check → filter gate → debounce arm → fire. The gate returns early ONLY when all four hold: watch-kind, filter configured, filename non-null, and non-matching.
**Invariant:** `filename !== null &&` is deliberate: null-filename events pass through UNFILTERED even when a filter is set, because dropping them could silently starve automations on platforms whose fs implementation doesn't provide names. A porter who "simplifies" the condition to `!match(filename)` breaks those platforms; one who drops the null-check branch entirely changes semantics the other way.
**Probe:** `packages/server/tests/folder-watch-manager.test.ts` (`passes events with a null filename through when a filter is set` :181–192 — due fires on null despite `*.mov` filter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "onFsEvent picomatch filter filename", limit: 10 });
```

## Verdict
Adopt the four-condition gate exactly; adapt the glob library (picomatch chosen for brace support). Directly tested including the brace-expansion matrix (`*.{mov,avi}` :205).
