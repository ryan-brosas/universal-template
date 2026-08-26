<!-- capsule-v2 -->
# qmd lifecycle — detect/embed/update scheduling with TTL caching, in-flight dedup, and background modes

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent keep a qmd index fresh in the background — detecting availability with TTL caching, deduping concurrent embeds, and debouncing updates — without ever blocking the session?

## qmd lifecycle
**Path/Symbol:** `index.ts:getQmdUpdateMode` (489–495), `qmdStatusTtl` (960–962), `detectQmd` (1074–1090), `checkCollection` (1092–1126), `ensureQmdEmbed` (1145–1161), `scheduleQmdUpdate` (1172–1180), `runQmdUpdateNow` (1182–1190), `ensureQmdAvailableForUpdate` (546–551).
**Signature:** `detectQmd(): Promise<boolean>`; `checkCollection(name): Promise<boolean>`; `ensureQmdEmbed(): boolean`; `scheduleQmdUpdate(): void`.
**Data Shape:** `QMD_STATUS_CACHE_TTL_MS = 5m` (positive), `QMD_STATUS_NEGATIVE_CACHE_TTL_MS = 5s`. `qmdCollectionStatusCache = Map<name, {checkedAt, exists}>`. `QMD_EMBED_TIMEOUT_MS = 10m`. Update mode from `PI_MEMORY_QMD_UPDATE` ∈ {background (default), manual, off}.

### Decisive source
```ts
// detectQmd (1074-1090): TTL-gated; `qmd collection list` is lighter than `qmd status`
if (qmdAvailabilityCheckedAt && now - qmdAvailabilityCheckedAt < qmdStatusTtl(qmdAvailable)) return Promise.resolve(qmdAvailable);
return new Promise((resolve) => {
  execFileFn("qmd", ["collection", "list"], { timeout: 15_000 }, (err) => {
    qmdAvailable = !err; qmdAvailabilityCheckedAt = Date.now(); resolve(qmdAvailable);
  });
});

// ensureQmdEmbed (1145-1161): in-flight dedup + pending queue so chunks written
// during an embed still get indexed right after
if (embedInFlight) { embedPending = true; return true; }
embedInFlight = true;
execFileFn("qmd", ["embed"], { timeout: QMD_EMBED_TIMEOUT_MS }, () => {
  embedInFlight = false;
  if (embedPending) { embedPending = false; ensureQmdEmbed(); }
});
return true;

// scheduleQmdUpdate (1172-1180): 500ms debounce before `qmd update`, then embed
updateTimer = setTimeout(() => { updateTimer = null; execFileFn("qmd", ["update"], { timeout: 30_000 }, () => ensureQmdEmbed()); }, 500);
```

**Flow:** (1) `detectQmd`/`checkCollection` cache results — positive for 5m, negative for 5s — so a user who installs qmd mid-session retries quickly. (2) `ensureQmdEmbed` dedupes concurrent embeds and queues a follow-up if one is already in flight. (3) `scheduleQmdUpdate` debounces `qmd update` by 500ms and chains an embed. (4) `ensureQmdAvailableForUpdate` lazily detects qmd only in background mode.

**Invariant:** availability checks are TTL-cached (positive 5m, negative 5s); at most one embed runs at a time with a pending follow-up; updates are debounced; nothing here blocks the session (all fire-and-forget with timeouts).

**Probe:** `test/unit.test.ts` — `scheduleQmdUpdate` describe (:653), `ensureQmdEmbed` describe (:705), `session_shutdown clears update timer` (:1403) and `session_shutdown is safe when no timer exists` (:1411) in the `lifecycle hooks` describe. Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "detectQmd checkCollection ensureQmdEmbed scheduleQmdUpdate getQmdUpdateMode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the TTL-cached availability detection, the in-flight-dedup embed with pending queue, the debounced update scheduling, and the background/manual/off mode gate. Adapt the TTLs, timeouts, and env-var name to the host. Omit nothing here — this is the portable qmd lifecycle core.
