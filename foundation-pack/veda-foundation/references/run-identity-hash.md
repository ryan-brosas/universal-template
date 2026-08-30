<!-- capsule-v2 -->
# Run identity hash — what must a resume-safety hash cover so resume is safe but not brittle?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A checkpointed pipeline must refuse resume when the user changed the prompt, the selected context, or the run options — but must not refuse on cosmetic changes. What exactly goes into the identity, and how is the mismatch surfaced?

## Content hash over prompt + context + options
**Path/Symbol:** `src/checkpoint/types.ts:computeRunIdentityHash` (:100-114); consumed by the three-arm gate in `src/commands/deep.ts:handleDeep` (:194-246, hash computed at :194-215 for validation and again at :386-395 for the fresh checkpoint).
**Signature:** `computeRunIdentityHash(inputs: { prompt: string; context?: string; options: Record<string, unknown> }) → string` (16 hex chars).
**Data Shape:** serialized as `JSON.stringify({prompt, context, options})`; hashed with `Bun.hash` (non-cryptographic, fast); output is `hash.toString(16).padStart(16, '0').slice(0, 16)`.

### Decisive source
```ts
export function computeRunIdentityHash(inputs: {
  prompt: string;
  context?: string;
  options: Record<string, unknown>;
}): string {
  const serialized = JSON.stringify({
    prompt: inputs.prompt,
    context: inputs.context,
    options: inputs.options,
  });
  // Use Bun's fast hash, take first 16 hex chars
  const hash = Bun.hash(serialized);
  return hash.toString(16).padStart(16, '0').slice(0, 16);
}
```
The handler's option projection (deep.ts :194-215) is deliberately NARROW — only `k`, `verify`, `categories`, `modules`, `lowCountModules`, and the listed-roster string `backend:model:reasoning` enter the hash. Display-only flags (notify, trace, output format) do NOT invalidate resume.

**Flow:** handler computes identity from the live inputs → compares against `existingCheckpoint.runIdentityHash` → match ⇒ resume proceeds; mismatch ⇒ loud stderr error naming `--force-resume` (resume anyway) vs `--force` (fresh), then `process.exit(1)`; `--force-resume` bypasses the check explicitly.
**Invariant:** the context string is part of identity — editing any selected file changes the context built from the selection store and therefore invalidates resume; the option set hashed is exactly the set that changes pipeline BEHAVIOR, so cosmetic flag changes never strand a checkpoint.
**Probe:** `tests/pipelines/deep-resume.test.ts` (executed live at pin: 10 pass / 0 fail) pins the resume path end-to-end; the hash function itself has no dedicated unit test — source-pinned probe: `bun -e 'import {computeRunIdentityHash} from "./src/checkpoint/types"; console.log(computeRunIdentityHash({prompt:"a",options:{}}) === computeRunIdentityHash({prompt:"a",options:{}}), computeRunIdentityHash({prompt:"a",options:{}}) !== computeRunIdentityHash({prompt:"b",options:{}}))'` → `true true`.
**Coverage caveat:** Bun.hash is not cryptographic — this guards against accidental mismatch, not adversarial tampering; a porter needing tamper evidence should swap in a keyed hash.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "computeRunIdentityHash runIdentityHash checkpoint resume mismatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the narrow-option content hash with loud mismatch UX naming both escape hatches. Adapt the hash primitive (Bun.hash → xxhash/BLAKE3) and the option projection to your pipeline's behavior-bearing flags. Omit the context-in-identity clause only if your context is immutable for a run's lifetime.
