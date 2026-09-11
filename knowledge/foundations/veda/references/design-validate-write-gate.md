<!-- capsule-v2 -->
# Design validation & persistence gate — how do you check all ten cross-reference invariants at once, then materialize the artifact as XML + JSON + human report?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** How do you validate a generated design's internal cross-references exhaustively (never short-circuiting), and where should its artifacts land so callers and humans can consume them after reboots?

## Connected graph-selected seam
**Path/Symbol:** `src/core/design/validate.ts:validateDesign` (:32–171) with `isRepoRelative` (:22–26); persistence twin `src/core/design/write.ts:writeDesign` (:153–174) with `designToXml` (:34–112), `designToReport` (:120–150), `esc` (:177–183).
**Signature:** `validateDesign(design: ProgramDesign): ValidateResult` where `ValidateResult = { ok, errors: ValidationError[], warnings: string[] }`; `writeDesign(design, validation, session): Promise<DesignOutputPaths>`.
**Data Shape:** `ValidationError = { kind: 'layout'|'signature'|'type'|'callstack'|'invariants'|'context', message }`; output triple `<sessionDir>/{design.xml, design.json, design.report}`.

### Decisive source
```ts
// 2. Every <callstack step ref=> must resolve to a declared signature.
const signatureNames = new Set(design.signatures.map(s => s.name));
for (const cs of design.callstacks) {
  if (cs.steps.length === 0) errors.push({ kind:'callstack', message:`callstack "${cs.name}" has no <step> elements` });
  for (const step of cs.steps) {
    if (!signatureNames.has(step.ref)) errors.push({ kind:'callstack',
      message:`callstack "${cs.name}" step ref="${step.ref}" does not resolve to any declared <signature>` });
  }
}
// ...
return { ok: errors.length === 0, errors, warnings };   // never short-circuits
```

**Flow:** index layout paths into a Set → run all ten checks collecting every error: duplicate layout paths; repo-relative path hygiene (`no leading /`, no `..`); signature/type files declared in layout; duplicate signature names (would make `<step ref=>` ambiguous); duplicate type names; callstack step resolution + non-empty callstacks; invariants required when signatures exist ("blunt rule replaces the unverifiable heuristic" per comment); used/omitted contradiction; layout∩omitted contradiction → two non-fatal warnings (empty layout / no signatures) → `ok = errors.length === 0`.
**Invariant:** exhaustive error collection — the designer model sees ALL problems in one round-trip instead of whack-a-mole; used-vs-omitted is derived purely from `reason === undefined`; validation is pure, write is the ONLY I/O layer in the pipeline (module docblock); artifacts go to `getSessionDir(session)` (project `.veda/sessions/<id>` in a git repo, else `$HOME/.config/veda/sessions/<id>`) — "survives reboots… avoids /tmp staleness" (Navigator finding recorded in source); XML re-emission escapes via `esc()` (&, <, >, ") making parse→write round-trippable.
**Probe:** repo-owned backtest executed at pin — `bun src/core/design/__probe__.ts`: **19/19 ALL GREEN**, pinning `validation ok:true`, `no errors`, plus every field of the parsed fixture that feeds this gate. No separate upstream spec file exists for validate.ts itself (coverage caveat: probe-level only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "validateDesign writeDesign designToXml designToReport ValidationError warnings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: kind-tagged exhaustive validation with warnings split from errors, pure validate + single-I/O-layer write, and the xml+json+report artifact triple in a reboot-surviving session dir. Adapt the invariant list to your artifact grammar (the ten here are Navigator-protocol-specific) and keep error messages self-describing enough for a model to fix its own output. Omit the specific `.veda` layout if your host has another session-dir convention — but keep it out of `/tmp`.
