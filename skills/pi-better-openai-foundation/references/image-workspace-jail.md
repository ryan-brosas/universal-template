<!-- capsule-v2 -->
# Workspace-jailed image inputs — how do you accept local image paths for an edit API without reading arbitrary files?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What validation ladder gates user-supplied image files before base64 upload?

## Input jail
**Path/Symbol:** `src/image.ts:readImageInputs` (:200-231), `validateImageInput` (:170-198), `isInsideDirectory` (:162-168); caps `MAX_IMAGE_INPUT_BYTES=20MB`, `MAX_IMAGE_INPUTS=5`, `MAX_TOTAL=50MB` (:23-25).
**Signature:** `readImageInputs(paths: string[] | undefined, cwd: string): Promise<ImageInput[]>`.
**Data Shape:** Output: `{path (real), mimeType, data (base64)}`; failure = thrown Error with `displayPath` (~-abbreviated) in the message.

### Decisive source
```ts
const path = isAbsolute(trimmed) ? resolve(trimmed) : resolve(workspaceRoot, trimmed);
if (!isInsideDirectory(workspaceRoot, path)) throw new Error("...inside the current workspace...");
realWorkspaceRoot ??= await realpath(workspaceRoot).catch(() => workspaceRoot);  // symlinked roots
const input = await validateImageInput(path, realWorkspaceRoot);
// validateImageInput: realpath(input) must be inside REAL root; stat().isFile();
// size ≤ 20MB; sharp metadata format ∈ {png,jpeg,jpg,webp,gif} else
//   throw "Image input is not a readable image"
...
if (seenPaths.has(input.path)) continue;                    // dedupe by REAL path
if (validatedInputs.length >= MAX_IMAGE_INPUTS) throw ...;
totalBytes += input.size;
if (totalBytes > MAX_TOTAL_IMAGE_INPUT_BYTES) throw ...;
```

**Flow:** per path: resolve → lexical containment → realpath BOTH sides → file/size/format checks → dedupe/count/budget accounting → parallel base64 reads only AFTER all validation.
**Invariant:** Containment is enforced against the REALPATH of the workspace (defeating a symlinked cwd escape) AND the realpath of each input (defeating symlinks inside it); format detection is content-based (sharp metadata), not extension-trust; bytes are read only after every gate passes.
**Probe:** `tests/image.test.ts` (:469 outside-workspace rejection incl. traversal, :499 non-file, :523 oversize 20MB+, :539/:551 max-count).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "readImageInputs validateImageInput isInsideDirectory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-realpath containment + content-sniffed formats + count/byte budgets before read. Adapt caps and allowed formats. Omit Codex endpoint wiring (request shape is product surface).
