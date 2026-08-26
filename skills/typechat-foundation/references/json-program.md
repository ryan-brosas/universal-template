<!-- capsule-v2 -->
# JSON program — how are @steps/@func/@ref programs compiled to TS and safely interpreted?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does a model-emitted JSON program get type-checked against a real API, and how is it evaluated without eval-level escape?

## createModuleTextFromProgram
**Path/Symbol:** `typescript/src/ts/program.ts:99-149`; schema text :6-32 (Program/FunctionCall/Expression/JsonValue/ResultReference); `createProgramTranslator` :215-238 swaps BOTH prompts onto a `TypeChatJsonTranslator<Program>`.
**Signature:** `(jsonObject: object): Result<string>` emitting:
```ts
import { API } from "./schema";
function program(api: API) { ... }
```
**Data Shape:** steps render as `const stepN = ...` with the LAST step as the function's `return`; `{"@ref": i}` renders as `step{i+1}` ONLY when index is an integer in `[0, currentStep)` AND the object has exactly one key (:124).

### Decisive source
```ts
else if (obj.hasOwnProperty("@func")) {
    const func = obj["@func"];
    const hasArgs = obj.hasOwnProperty("@args");
    const args = hasArgs ? obj["@args"] : [];
    if (isValidFunctionName(func) && (Array.isArray(args)) && Object.keys(obj).length === (hasArgs ? 2 : 1)) {
        return `api.${func}(${arrayToString(args)})`;
    }
}
...
function isValidFunctionName(name: unknown): name is string {
    return typeof name === "string" &&
        /^[a-zA-Z_$][0-9a-zA-Z_$]*$/.test(name) &&
        !Object.prototype.hasOwnProperty.call(Object.prototype, name);
}
```
**Flow:** any failed node sets closure flag `hasError` → whole module rejected ("JSON program contains an invalid expression") — no partial output ever reaches the compiler.
**Invariant:** identifier regex + Object.prototype membership veto (`constructor`, `__proto__`, `toString`, `valueOf`, `hasOwnProperty`) is the injection wall for CODE GENERATION; exact-key-count checks reject smuggled extra keys. Direct tests pin comment-injection attempts (`play('x'); /*`) failing closed at BOTH compile and evaluate.

## evaluateJsonProgram
**Path/Symbol:** `typescript/src/ts/program.ts:160-205`.
**Signature:** `async evaluateJsonProgram(program, onCall: (func: string, args: unknown[]) => Promise<unknown>): Promise<unknown>` — returns LAST step's value, undefined for zero steps.
**Flow:** sequential await per step into `results[]` (refs resolve against COMPLETED prefix only) → objects evaluate their values via `Promise.all` then reassemble keys → arrays fan out concurrently → `@ref` out-of-range/non-integer/multi-key ⇒ throw `Invalid result reference`; bad name/shape ⇒ `Invalid function call/name`.
**Invariant:** unlike the compiler (which rejects wholesale), the INTERPRETER throws mid-run after earlier calls may have dispatched — host code must treat dispatch as side-effectful up to the throw. The same isValidFunctionName guard protects DISPATCH (host callback receives only vetted names), so access control lives entirely in onCall.
**Probe:** `grep -c 'Object.prototype.hasOwnProperty.call(Object.prototype' typescript/src/ts/program.ts` (=1); live pins `typescript/test/program.test.ts`: :30-58 negative/0.5/out-of-bound refs throw at evaluate AND fail at compile; :150-163 prototype-member names never dispatch (calls.length===0); :184-234 non-array @args and extra keys rejected both paths.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"evaluateJsonProgram createModuleTextFromProgram","limit":5}'
// exactly rank1+rank2 on this file pair
```

## Verdict
Adopt both halves together — compile-time rejection gives repairable diagnostics, interpreter guards give defense-in-depth; adapt step naming if hosts need parallel execution (current semantics are strictly sequential); omit the TS-module emission and keep only the interpreter if you validate programs by other means.
