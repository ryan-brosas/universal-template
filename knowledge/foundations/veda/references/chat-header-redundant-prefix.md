<!-- capsule-v2 -->
# Chat header redundant-prefix strip — how do you render a backend/model identity line without duplicating the backend prefix?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** One backend (pi) returns canonical full model strings like `pi/provider/model`, while the header already prints the backend name. Naive interpolation renders `pi/pi/provider/model`. How is the identifier line built?

## Strip the backend prefix from the model before interpolation
**Path/Symbol:** `src/util/trace-format.ts:formatChatHeader` (:318-355, strip at :339); direct test `tests/util/trace-format.test.ts` (:258-278, the two `pi/pi/` negative pins).
**Signature:** `formatChatHeader(persona: string | undefined, backend: string, model: string | undefined, width = FORMAT_CONFIG.lineWidth, sandbox?: string) → string`.
**Data Shape:** four identifier arms: persona+model → `persona (backend/model)`; persona only → `persona (backend)`; model only → `backend/model`; neither → `backend`. Optional ` · sandbox` suffix; padded with `─` to exactly `width` chars.

### Decisive source
```ts
  // Build the identifier: "persona (backend/model)" or "backend/model" or just "backend"
  // Strip a redundant backend prefix from the model so pi's canonical
  // "pi/provider/model" doesn't render as "pi/pi/provider/model".
  const displayModel = model && model.startsWith(`${backend}/`) ? model.slice(backend.length + 1) : model;
  let identifier: string;
  if (persona && displayModel) {
    identifier = `${persona} (${backend}/${displayModel})`;
  } else if (persona) {
    identifier = `${persona} (${backend})`;
  } else if (displayModel) {
    identifier = `${backend}/${displayModel}`;
  } else {
    identifier = backend;
  }
```
**Flow:** compute `displayModel` by stripping ONLY an exact `${backend}/` prefix (first occurrence, anchored at position 0 — a model that merely contains the backend string elsewhere is untouched) → select the identifier arm by persona/model presence → append the sandbox suffix when provided → pad with separator dashes so the ANSI-stripped line is exactly `width` chars.
**Invariant:** the rendered header never contains a doubled backend segment (`pi/pi/`); the strip is prefix-anchored so `pi/wafer/glm-5.1` under backend `pi` renders `pi/wafer/glm-5.1` (only the leading `pi/` is removed), and a foreign model string under a different backend passes through unchanged. Width is exact, not minimum — the test asserts `stripped.length === 80`.
**Probe:** `tests/util/trace-format.test.ts` (executed live at pin: 45 pass / 0 fail across the file) pins both negative cases: `expect(stripped).not.toContain('pi/pi/')` at :270 and :277, plus the width-exactness assertion.
**Coverage caveat:** the four identifier arms are fully test-pinned; the sandbox suffix arm is exercised only via the worker-run integration suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "formatChatHeader displayModel startsWith backend prefix strip identifier sandbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix-anchored strip before identity interpolation whenever a backend can return self-prefixed canonical model strings. Adapt the arm set (persona/sandbox vocabulary) to your host. Omit nothing if your backends never self-prefix — but keep the width-exactness contract.
