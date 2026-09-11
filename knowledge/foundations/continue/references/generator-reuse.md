<!-- capsule-v2 -->
# Generator reuse — keep the in-flight generation alive while the user keeps typing

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When the user types more characters while the model is still streaming, how does Continue reuse the running generator instead of cancelling and restarting per keystroke?

## The reuse manager
**Path/Symbol:** `core/autocomplete/generation/GeneratorReuseManager.ts` (whole, 85L).
**Signature:** `getGenerator(prefix: string, newGenerator: (abortSignal) => AsyncGenerator<string>, multiline: boolean): AsyncGenerator<string>`.
**Data Shape:** tracks `currentGenerator`, `pendingGeneratorPrefix`, `pendingCompletion`; wraps generators in a `ListenableGenerator` that accumulates `pendingCompletion` as chunks flow.

### Decisive source
```ts
private shouldReuseExistingGenerator(prefix: string): boolean {
  return (
    !!this.currentGenerator && !!this.pendingGeneratorPrefix &&
    (this.pendingGeneratorPrefix + this.pendingCompletion).startsWith(prefix) &&  // everything typed already in streamed text
    this.pendingGeneratorPrefix?.length <= prefix?.length                          // e.g. backspace guard
  );
}
async *getGenerator(prefix, newGenerator, multiline) {
  if (!this.shouldReuseExistingGenerator(prefix)) {
    const abortController = new AbortController();
    this._createListenableGenerator(abortController, newGenerator(abortController.signal), prefix);
  }
  let typedSinceLastGenerator = prefix.slice(this.pendingGeneratorPrefix?.length) || "";
  for await (let chunk of this.currentGenerator?.tee() ?? []) {
    if (!chunk) continue;
    // strip already-typed characters from yields
    while (chunk.length && typedSinceLastGenerator.length) {
      if (chunk[0] === typedSinceLastGenerator[0]) { typedSinceLastGenerator = typedSinceLastGenerator.slice(1); chunk = chunk.slice(1); }
      else break;
    }
    const newLineIndex = chunk.indexOf("\n");
    if (newLineIndex >= 0 && !multiline) { yield chunk.slice(0, newLineIndex); break; }
    else if (chunk !== "") yield chunk;
  }
}
```

**Flow:** if `(pendingGeneratorPrefix + pendingCompletion).startsWith(prefix)` — i.e. everything the user typed is already contained in the streamed-so-far completion — the RUNNING generator is reused instead of cancelled. Already-typed characters are stripped from yielded chunks by a consume loop comparing char-by-char against `typedSinceLastGenerator`. Backspace protection: reuse requires `pendingGeneratorPrefix.length <= prefix.length`. Non-multiline mode breaks at the first newline in a chunk, yielding only up to it.

**Invariant:** reuse requires the pending prefix+completion to remain a prefix of the new prefix AND the pending prefix to be no longer than the new prefix (backspace forces a restart); already-typed characters are never re-yielded; the previous generator is cancelled (`currentGenerator?.cancel()`) only when a NEW generator is created.

**Probe:** `core/autocomplete/generation/GeneratorReuseManager.vitest.ts` (223L) — "reuses generator when prefix matches pending completion" (newGenerator called once, second call yields only `["world"]`), "creates new generator when prefix does not match", "handles multiline=false by stopping at newline", "cancels previous generator when creating a new one", "handles backspacing by creating new generator when prefix is shorter", "calls onError when generator throws".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "GeneratorReuseManager getGenerator shouldReuseExistingGenerator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix-containment reuse check, the char-stripping consume loop, the backspace guard, and the multiline newline break; adapt nothing host-specific; omit the `ListenableGenerator` teeing internals unless a target needs the listenable wrapper. Coverage caveat: graph metadata `metadata_match`; direct vitest suite pins all invariants.
