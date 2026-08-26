<!-- capsule-v2 -->
# Randomized search-combo walk — how do I diversify WHICH searches a bot runs so its query pattern stops being a sequential bot signature?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`start_apply` :222–238); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** how do you enumerate every (query, filter) combination you intend to scrape while randomizing visit order and bounding total work?

## Shuffle-at-enumeration over positions × locations
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.start_apply` (:222–238); delegates each accepted pair to `applications_loop` (:242).
**Signature:** `start_apply(positions: list, locations: list) -> None`; draws `random.randint(0, len(xs)-1)` for both axes per iteration.
**Data Shape:** `combos: list[tuple]` accumulates ACCEPTED pairs only; loop continues while `len(combos) < len(positions) * len(locations)`; hard break when `len(combos) > 500`.

### Decisive source
```python
def start_apply(self, positions, locations) -> None:
    start: float = time.time()
    self.fill_data()                      # park window off-screen first
    combos: list = []
    while len(combos) < len(positions) * len(locations):
        position = positions[random.randint(0, len(positions) - 1)]
        location = locations[random.randint(0, len(locations) - 1)]
        combo: tuple = (position, location)
        if combo not in combos:            # rejection sampling = shuffled order
            combos.append(combo)
            log.info(f"Applying to {position}: {location}")
            location = "&location=" + location
            self.applications_loop(position, location)
        if len(combos) > 500:              # runaway guard for huge cross-products
            break
```

**Flow:** park browser → repeatedly draw a RANDOM (position, location) pair from the cross-product → reject already-seen pairs (list membership) → immediately run that search's application loop → stop when every pair has run once, or past 500 pairs.
**Invariant:** every accepted pair is processed EXACTLY once (membership check precedes append+run), and the processing ORDER is randomized at enumeration time — an observer sees unrelated searches back-to-back instead of position-by-position sweeps; the >500 break bounds worst-case runtime independent of product size. Note the trade-off: rejection sampling degrades toward O(n²) draws as the product fills (fine for dozens of combos, wrong for thousands — shuffle the product list instead).
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified byte-for-byte at HEAD 8471c58: `grep -n "randint\|combos" easyapplybot.py` ⇒ :227/:228/:229/:230/:232/:233/:237 (single mechanism site); `grep -n "combos" easyapplybot.py` shows NO other mutation site (no reset between calls).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "start_apply positions locations combos", limit: 5 });
// ⇒ EasyApplyBot.start_apply :222-238 (resolved live this pass)
```

## Verdict
Adopt enumerate-randomized-once semantics with a hard work bound — it composes with inbox-harvest-shuffle (which shuffles WITHIN one list; this shuffles WHICH lists you open) into full activity-path randomization; adapt the dedupe container to a set and prefer Fisher-Yates over rejection sampling for large products; omit the tuple-mutation quirk of rewriting `location` into a query-string fragment inside the loop (build wire params where they're used). Caveat: source-read only, no upstream tests.