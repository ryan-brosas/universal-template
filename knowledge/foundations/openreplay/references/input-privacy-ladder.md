<!-- capsule-v2 -->
# Input default-obscured ladder — which heuristic decides a field is sensitive when no attribute exists?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** In what order must password/hidden/obscured heuristics apply so a porter reproduces the privacy defaults exactly?

## Escalation ladder inside getInputValue
**Path/Symbol:** `tracker/tracker/src/main/modules/input.ts` — `getInputValue` (:148–176), `Options.defaultInputMode` (:120, default `Obscured` :129), `INPUT_TYPES` (:13–23).
**Signature:** `getInputValue(id: number, node: TextFieldElement | HTMLSelectElement): { value: string; mask: number }`.
**Data Shape:** `defaultInputMode: 0|1|2` (Plain/Obscured/Hidden). Heuristic inputs: sanitizer level for the node's id, `node.type`, presence of `\d\d\d\d`, `@` in value, `type==='date'`.

### Decisive source
```ts
if (node.type === 'password' || app.sanitizer.isHidden(id)) {
  inputMode = InputMode.Hidden
} else if (
  app.sanitizer.isObscured(id) ||
  (inputMode === InputMode.Plain &&
    ((options.obscureInputNumbers && node.type !== 'date' && /\d\d\d\d/.test(value)) ||
      (options.obscureInputDates && node.type === 'date') ||
      (options.obscureInputEmails && (node.type === 'email' || !!~value.indexOf('@')))))
) { inputMode = InputMode.Obscured }
```

**Flow:** Hidden beats Obscured beats Plain. Password fields are always Hidden regardless of attributes; DOM-sanitizer level can force Obscured even when the numeric/email heuristics would allow plain text; the four-digit regex only fires when the user explicitly chose Plain as default (opt-in to capture).
**Invariant:** The heuristics may only RAISE sensitivity above `defaultInputMode`, never lower it below an attribute-driven level. Date exclusion (`type !== 'date'`) prevents double-masking when `obscureInputDates` is on.
**Probe:** `grep -c "node.type === 'password' || app.sanitizer.isHidden(id)" tracker/tracker/src/main/modules/input.ts` → `1`; `grep -c 'defaultInputMode: InputMode.Obscured' tracker/tracker/src/main/modules/input.ts` → `1`; direct test `tests/input.test.ts` pins label resolution (suite executed green); behavior boundary documented by `tests/sanitizer.unit.test.ts`.
**Coverage:** input.ts + sanitizer.ts both clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "getInputValue defaultInputMode obscure hidden ladder", limit: 10 });
```

## Verdict
Adopt the ladder order (password→hidden, attribute→obscured, heuristics→plain-gated). Adapt the `\d\d\d\d` / `@` heuristics to your product's PII definition. Omit select-element tracking if your replay only needs text fields.
