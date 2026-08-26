<!-- capsule-v2 -->
# JSONL torn-tail repair — when may a loader rewrite a damaged session file, and when must it refuse?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c`; Codebase Memory `pi-upstream`. **Question:** A porter loading an append-only session log after a crash must decide which trailing garbage is safe to truncate versus corruption to surface — what is the exact rule?

## Load-time triage in JsonlSessionStorage.load
**Path/Symbol:** `packages/agent/src/harness/session/jsonl/storage.ts:69-108` (`JsonlSessionStorage.load`), `:33-46` (`publishFileAtomically`).
**Signature:** `static async load(fs, path): Promise<JsonlSessionStorage>`; helper `publishFileAtomically(fs, destinationPath, populate)` stages a complete sibling `<dest>.tmp` then renames over the destination.
**Data Shape:** File = line 1 header (`kind:"header", version:4`) + one mutation JSON object per following line, each terminated `\n`. Decode errors split into `kind:"syntax"` (invalid JSON) vs `kind:"schema"` (valid JSON, wrong shape) via `JsonlDecodeError`.

### Decisive source
```ts
const mutationResult = parseMutation(line);
if (!mutationResult.ok) {
    const isTornTail = index === physicalLines.length - 1 && mutationResult.error.kind === "syntax";
    if (isTornTail) {
        // Drop the unacknowledged partial append by atomically publishing the valid prefix.
        const validPrefix = `${physicalLines.slice(0, index).join("\n")}\n`;
        await publishFileAtomically(fs, path, async (tempPath) => {
            fileResult(await fs.writeFile(tempPath, validPrefix), `Failed to stage torn-tail repair ${path}`);
        });
        return storage;
    }
    throw invalidFile(path, index + 1, mutationResult.error);
}
```

**Flow:** read whole file → pop single trailing empty split artifact → parse header (fail hard) → for each mutation line: parse; if it fails AND it is the last line AND the failure is pure JSON syntax, atomically republish just the valid prefix and continue; ANY other failure (schema error on last line, syntax or schema error mid-file) throws without touching the file → after all lines, if content lacked a final `\n`, repair by appending one.
**Invariant:** Only a *syntactically broken final line* is presumed an interrupted append (the writer appends whole lines, so a partial tail can never carry acknowledged state). A *well-formed JSON line that fails validation is semantic corruption* — never auto-truncated, because it may be evidence of disk corruption or a hostile edit. All rewrites go through tmp+rename so a crash during repair leaves either old file or repaired file, never a half-written one. Writes are serialized through the promise-tail queue (`enqueue`, :258-265: chain on `this.tail`, swallow its rejection so one failed append doesn't poison later ops) preserving the append→apply ordering (file first, then memory).
**Probe:** `packages/agent/test/harness/session/jsonl.test.ts` — `"truncates a malformed final line"` (:472: append `{"kind":"entry"`, reopen → 1 entry kept, bytes == validPrefix, next append gets seq 2); `"rejects a complete invalid final mutation without modifying the file"` (:489: `{kind:"unknown"}` last line → rejects code `invalid_entry`, file byte-identical); `"repairs a valid final line missing its newline"` (:426).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "JsonlSessionStorage load torn tail mutation", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves `JsonlSessionStorage.load` at `storage.ts:69-108` rank #1.)

## Verdict
Adopt the three-way triage (syntax-final-line = truncate atomically; schema-invalid anywhere = refuse loudly; missing final newline = append repair) and tmp+rename publication for every log rewrite. Adapt the decode taxonomy to your serializer's error kinds. Omit the shared `.tmp` caller-serialization contract only if your host has no concurrent publishers of the same destination. Coverage: direct tests exist for truncate/reject/newline-repair paths at this pin; no test covers rename failure mid-repair (staging-failure tests cover fork instead).
