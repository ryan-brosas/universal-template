<!-- capsule-v2 -->
# Kitty frame manager — how do you animate images in a kitty-compatible terminal without leaking graphics memory across frames?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the upload/delete/place choreography for looping terminal image animation?

## Kitty animator
**Path/Symbol:** `src/pets.ts:class CodexPetKittyManager` (:692-765); encoders `encodeKittyRawRgbaData` (:659-681), placement/delete builders (:647-657); id allocation `kittyImageBaseForPet` (:477-481).
**Signature:** `renderFrame(frame, width, {sizeCells}): string[]`; `queueCleanup/invalidate/dispose/takeCleanupSequence`.
**Data Shape:** Raw RGBA uploaded as base64 in ≤4096-char chunks with `m=1/m=0` continuation flags; per-frame stable ids `0x50000000 + hash(slug)*100 + offset`.

### Decisive source
```ts
// Per-frame render sequence:
const deletePrevious = this.previousFrameImageId !== frameImageId
  ? deleteCodexPetKittyPlacement(this.previousFrameImageId) : "";
const deleteCurrent = deleteCodexPetKittyPlacement(frameImageId);
// Do not cache uploads across animation loops... failures are suppressed with q=2
// and otherwise show up as an occasionally invisible pet.
const upload = encodeKittyRawRgba(frame, frameImageId);
this.previousFrameImageId = frameImageId;
const hostCleanupSentinel = frameImageId !== this.placementImageId
  ? deleteCodexPetKittyPlacement(this.placementImageId) : "";
const sequence = `${hostCleanupSentinel}${deletePrevious}${deleteCurrent}${upload}${placeKittyImage(...)}`;
lines.push(moveUp + sequence + moveDown);   // rows-1 blank lines + cursor dance
```
Cleanup ledger: `queueCleanup(pet)` collects every frame's id into a pending Set; `takeCleanupSequence()` emits placement-delete + all image deletes ONCE and clears (:714-728). Host-owned-id hazard documented in-source: recent pi-tui frees kitty ids it owns on changed lines, so the FIRST command targets the harmless footer-placement id, never a live frame id (:750-756).

**Flow:** frame N: delete previous placement → delete current placement → RE-UPLOAD full RGBA → place at cell size → emit blank rows + cursor-up/down wrapper; loop repeats without caching uploads; on hide/resize/shutdown the pending set drains one batched delete sequence.
**Invariant:** Never reuse an upload across loops (terminals may drop data after clears/quota — q=2 hides ACK errors, symptom = invisible pet); ids are deterministic per pet (hash base) so placements survive re-renders; deletes always precede uploads for the same id.
**Probe:** `tests/pets.test.ts` (:105 synthetic kittyFrame fixtures, chunking/id assertions in kitty-manager tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "CodexPetKittyManager renderFrame encodeKittyRawRgbaData takeCleanupSequence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delete→upload→place per frame + pending-set batched cleanup + sentinel-first ordering. Adapt image ids/sizing. Omit iTerm protocol path (separate Image component).
