<!-- capsule-v2 -->
# Pet asset jail — how do you load user-supplied image assets from an untrusted directory without path escape or symlink attacks?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What validation ladder makes a community spritesheet safe to open with a native image decoder?

## Asset validation
**Path/Symbol:** `src/pets.ts:resolvePetAssetPath` (:157-161), `isPathInsideDirectory` (:150-155), `validatePetSpritesheet` (:170-213); catalog cache :37, :215-221, :289-302; lookup `petLookupKey`/`findCodexPet` (:304-384).
**Signature:** `validatePetSpritesheet(petDir, spritesheetPath): Promise<string | undefined>` (undefined = valid, string = reason); `listCodexPets(home, {refresh?}): Promise<CodexPetPackage[]>`.
**Data Shape:** Atlas contract: exactly 1536×1872 webp/png (8 cols × 9 rows of 192×208 cells); pet.json supplies displayName/name/description/spritesheetPath.

### Decisive source
```ts
const resolvedSpritesheetPath = resolvePetAssetPath(petDir, spritesheetPath);
if (!resolvedSpritesheetPath) return `invalid spritesheetPath outside pet folder: ...`;
let fileStat = await lstat(resolvedSpritesheetPath).catch(...);
if (fileStat.isSymbolicLink()) return `${spritesheetPath} must not be a symlink`;
if (!fileStat.isFile()) return `${spritesheetPath} is not a file`;
const realPetDir = await realpath(petDir).catch(() => undefined);
const realSpritesheetPath = await realpath(resolvedSpritesheetPath).catch(() => undefined);
if (!realPetDir || !realSpritesheetPath || !isPathInsideDirectory(realPetDir, realSpritesheetPath))
  return `invalid spritesheetPath outside pet folder: ${spritesheetPath}`;   // symlinked DIRS too
...
const metadata = await sharp(resolvedSpritesheetPath, { animated: false }).metadata();
if (metadata.width !== EXPECTED_ATLAS_WIDTH || metadata.height !== EXPECTED_ATLAS_HEIGHT)
  return `invalid atlas dimensions: ${w}x${h}; expected ${EXPECTED_ATLAS_WIDTH}x${EXPECTED_ATLAS_HEIGHT}`;
```
Catalog reads run at bounded concurrency 4 via index-claim worker loop (`PET_CATALOG_READ_CONCURRENCY`) and cache per resolved-home for 1500ms (:27, :269-302) so autocomplete bursts don't re-stat. Fuzzy selection normalizes NFKC + strips non-letters across slug|id|name with exact-before-fuzzy precedence (:304-365).

**Flow:** resolve within pet dir → lstat reject-symlink → realpath BOTH ends re-contained → readable check → sharp metadata dimension pin → package marked ready; every failure returns a human-readable issue STRING that surfaces in `/pets list`, never throws.
**Invariant:** Validation is fail-closed with reasons (issue strings are data); containment is checked TWICE — lexical resolve AND realpath — defeating `..` traversal and directory symlinks alike; the atlas dimensions are exact because frame extraction arithmetic depends on them.
**Probe:** `tests/pets.test.ts` (:306 symlinked spritesheet rejected "must not be a symlink", :334 catalog cache reuse, :368 explicit refresh bypass, :170 punctuation-only lookup miss).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "validatePetSpritesheet resolvePetAssetPath listCodexPets", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual containment + symlink refusal + exact-dimension gate + issue-string diagnostics. Adapt atlas geometry and metadata fields. Omit Codex-specific pet.json conventions.
