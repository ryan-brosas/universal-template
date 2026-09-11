<!-- capsule-v2 -->
# Functional-errors-only type gate — a lenient TypeScript pass that catches breakage, not style, and doubles as the TS→JS transpiler

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** guest code is an untrusted function body with host globals (`pi`, `agents`, …) — how do you reject genuinely broken programs (misspelled names, unknown globals) WITHOUT drowning models in strict-null noise, and where does the emitted JavaScript come from?

## Connected graph-selected seam
**Path/Symbol:** `src/runtime/type-checker.ts` whole file (182L): `compilerOptions` (:15-31), `TYPE_CORRECTNESS_CODES` (:33-38), `normalizeTypeScriptPath` (:42-43), `FabricTypeChecker` (:45-149 — in-memory CompilerHost :80-105, `check` :108-148), LRU `checkerCache` + `MAX_CHECKERS = 4` (:151-169), `transpileFabricCode` (:171-177), `typeCheckFabricCode` (:179-182).
**Signature:** `typeCheckFabricCode(code, declarations)` → `{errors: FabricTypeError[], javascript?: string}`; `FabricTypeError {line, column, message}` with USER-FACING line numbers (guest body line 1 = wrapper line 2).
**Data Shape:** code wrapped as `` async function __piFabricMain() {\n<code>\n} `` — identical wrapper in check AND transpile paths.

### Decisive source
```ts
const TYPE_CORRECTNESS_CODES = new Set<number>([
  2339, 2551,          // property does not exist / did you mean
  2322, 2345, 2367,    // assignment / argument / comparison mismatches
  2531, 2532, 18047, 18048, // possibly-null object/function
  7006, 7008, 7019, 7031-7034, // implicit-any family
]);
// ...
...program.getSemanticDiagnostics(this.#sourceFile)
    .filter((diagnostic) => !TYPE_CORRECTNESS_CODES.has(diagnostic.code)),
// ...
this.#sourceText = `async function __piFabricMain() {\n${code}\n}\n`;
```

**Flow:** ONE checker instance per declarations string lives in an LRU (re-insert on hit; evict oldest beyond 4) so repeated executions skip rebuilding lib/declaration programs. The in-memory CompilerHost serves ONLY two virtual files — guest `.ts` (rewritten each check) and globals `.d.ts` (the guest API surface; mode-dependent: `guestTypeDeclarations(effectiveFullCodeMode)` omits `pi`/`extensions` declares outside full-code) — everything else falls through to the base host with a stable-file cache. Diagnostics = syntactic + semantic MINUS the allowlisted correctness codes; errors map to 1-based positions via `getLineAndCharacterOfPosition` with `line: Math.max(1, position.line)` (wrapper offset folded). Zero errors ⇒ `program.emit` captures the `.js` output which execution-service forwards as `options.transpiledCode` so the runtime never re-transpiles. A separate cheap `transpileFabricCode` path exists for runtimes invoked without checking.
**Invariant:** (1) STRICTNESS IS DELIBERATELY OFF (`strict:false`, noImplicitAny:false, strictNullChecks:false …) and the remaining type-error classes are BLOCKLISTED by diagnostic code — the gate only rejects what would actually break at runtime (undefined identifiers, wrong shapes on first-class provider args like `compact.request({reasno})`) while letting `path: 42` reach runtime validation (pinned by test comment). (2) The wrapper is PART of the checked text, so reported lines are shifted by exactly one — `line: Math.max(1, position.line)` + `column + 1` restore user coordinates; a diagnostic with no file/start degrades to `{line:0,column:0}` which the UI renders message-only. (3) Windows backslash paths are normalized before canonical comparison — otherwise the host treats `C:\__pi_fabric_guest_1.ts` as missing. (4) Declarations are keyed by EXACT STRING in the LRU: full-code vs orchestration-only modes produce different declaration strings ⇒ different cached checkers, never cross-contaminated. (5) Type-check failure returns BEFORE any sandbox spawn and with EMPTY audits — "code was not executed" is structural (execution-service seals trace "failed"), not just wording. (6) `skipLibCheck:true` keeps the pass fast; the stable-file cache means only the tiny guest file re-parses per call.
**Probe:** `tests/type-checker.test.ts:9` ("normalizes Windows paths for TypeScript compiler host comparisons"), `:15` ("accepts typed Fabric code with top-level return" — emits JS containing the wrapper, stripped of type annotations), `:90` ("rejects misspelled first-class provider argument keys"), `:99` ("keeps first-class Fabric providers typed in orchestration-only mode" — declarations omit pi/extensions), `:157` ("reports user-facing line numbers for functional errors" — `Cannot find name` at line 1). End-to-end zero-work round trip: `tests/execution-service.test.ts:449` direct-call branch asserts `Cannot find name 'pi'`; `tests/type-error-guidance.test.ts` pins the recovery hint text.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "typeCheckFabricCode FabricTypeChecker checkerFor transpileFabricCode TYPE_CORRECTNESS_CODES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the blocklist-of-diagnostic-codes functional gate over an in-memory two-file CompilerHost with declaration-keyed LRU reuse, and take the emitted JS as the sandbox input; adapt the declaration surface to your host API. Porters get this wrong by running stock strict TS (models drown in nullability noise) or by forgetting the wrapper-offset line shift (every error points one line high).
