<!-- capsule-v2 -->
# Preview-carrying write tool — how do you wrap a host write tool so every mutation carries a bounded before-diff, without losing queue serialization or abort discipline?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** where in a wrapped tool's execute() do you capture the previous file state so the UI gets a code preview, while keeping per-path mutation queuing and abort checks intact?

## Read-before-write inside the host's file-mutation queue, preview attached to details
**Path/Symbol:** `src/providers/write-preview.ts` whole file (112L): `resolvePreviewPath` (:22-28), `skipped` envelope (:30-40), `readExistingFileForPreview` (:45-74), `createPreviewWriteToolDefinition` (:76-112). Consumer: `src/providers/pi-tools-provider.ts:186` (`write: createPreviewWriteToolDefinition(cwd)`). Adapted from pi-code-previews with Fabric result isolation (THIRD_PARTY_NOTICES header).
**Signature:** `createPreviewWriteToolDefinition(cwd): ToolDefinition`; execute returns `{content:[{type:"text", text:"Successfully wrote N bytes to <path>"}], details:{codePreviewBeforeWrite}}`.
**Data Shape:** `codePreviewBeforeWrite: {kind:"content", content} | {kind:"skipped", reason, byteLength?, maxBytes, sizeExceeded?} | undefined` (undefined = path did not exist → clean create).

### Decisive source
```ts
return withFileMutationQueue(absolutePath, async () => {
  const throwIfAborted = () => { if (signal?.aborted) throw new Error("Operation aborted"); };
  throwIfAborted();                                   // before read
  const before = await readExistingFileForPreview(path, cwd, content);
  throwIfAborted();                                   // before mkdir
  await mkdir(dirname(absolutePath), { recursive: true });
  throwIfAborted();                                   // before write
  await writeFile(absolutePath, content, "utf8");
  throwIfAborted();
  return { content: [/* … */], details: { codePreviewBeforeWrite: before } };
});
```

**Flow:** resolve the target path (`~`/`~/` expansion, `@`-prefix strip, Unicode-space normalization `\u00a0\u2000-\u200a\u202f\u205f\u3000` → plain space) INSIDE the same cwd as the original tool; enqueue on the host package's `withFileMutationQueue` for the absolute path so concurrent writes serialize; read the existing file with a five-arm skip ladder: next-content over `MAX_WRITE_DIFF_BYTES` → `skipped("new content too large", sizeExceeded:true)` BEFORE stat (:52-54); stat ENOENT → undefined (clean create); stat other error → `previous content unavailable`; not a regular file → `previous path is not a regular file`; stat.size or read bytes > cap → `previous file too large` (sizeExceeded). Every skip envelope carries `maxBytes` for downstream rendering decisions.
**Invariant:** the preview read happens AFTER acquiring the per-file mutation lock and BEFORE `mkdir`/`writeFile`, so captured "before" state can never race another writer; abort is re-checked at each await boundary — an aborted call never leaves a half-written file silently (the throw propagates before writeFile); the wrapper REPLACES only `execute`, spreading all other tool-definition fields (`...original`) so schema/description stay the host's.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "writeContentForPreview(nextContent)" src/providers/write-preview.ts | wc -l'` → 1 (:52); `grep -cF "throwIfAborted()" src/providers/write-preview.ts` → 4; `grep -n "withFileMutationQueue(absolutePath" src/providers/write-preview.ts | wc -l` → 1 (:89); `grep -n "codePreviewBeforeWrite" src/providers/write-preview.ts | wc -l` → 1 (:107 details envelope; the capture variable itself is `before` at :94).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "createPreviewWriteToolDefinition write tool codePreviewBeforeWrite mutation queue", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `createPreviewWriteToolDefinition` :76-112 line-exact.)

## Verdict
Adopt read-before-write under a per-path mutation lock with typed skip envelopes carrying maxBytes for any tool wrapper that must feed diff previews to a UI; adapt the path-normalization ladder to your shell vocabulary; omit the abort re-checks if your runtime serializes calls synchronously. Coverage caveat: behavior exercised indirectly through pi-tools-provider suites and dashboard render tests; no dedicated spec imports this wrapper.
