<!-- capsule-v2 -->
# TypeScript dosage rule — which two offerings does TS bundle, and what's the deliberate minimal stance?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** When does adopting TypeScript reduce rather than improve complexity?

## Type-safety ⊥ advanced design constructs are MUTUALLY EXCLUSIVE offers; adopt types deliberately; plain functions+primitive types = lower complexity
**Path/Symbol:** `sections/projectstructre/typescript-considerations.md` (:7 two-offerings split + law-of-the-instrument, :17-19 15%-bug research, :21-23 TS-tax counterpoint).
**Signature:** recommended posture: "classic JavaScript, plain functions and objects, ... simply decorated with primitive types"; caution against unchosen drift into abstract classes/interfaces/namespaces/OOP.
**Data Shape:** two bundled value propositions — (1) type safety incl. editor completions over historical JS libs, (2) advanced design constructs (abstract classes, interfaces, namespaces). Research anchor: static typing detects ~15% of public bugs (Flow 0.30 / TS 2.0 study).

### Decisive source
```text
# typescript-considerations.md :7
TypeScript actually brings two mutually-exclusive offerings to the table:
type-safety and advanced design constructs like abstract classes,
interfaces, namespaces and more. Many teams chose TypeScript for better type
safety yet unintentionally, without any proper planning, use it for other
purposes, such as OOP.
```

**Flow:** teams adopt TS for bug reduction → law of the instrument ('if an abstract class exists in the toolbox — developers will use it') silently converts them to OOP design → complexity rises though only type safety was wanted → remedy: CONSCIOUSLY choose which offering you adopt; if only types: keep plain functions/objects decorated with primitive types.
**Invariant:** the 15% detection figure cuts BOTH ways — the remaining ~85% still needs tests/lint/review ("TypeScript will always miss 80% of bugs" tax argument :23), so its cost applies either way and doesn't displace other quality gates. Type adoption must be a planned decision, not toolchain osmosis.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'mutually-exclusive' sections/projectstructre/typescript-considerations.md` >= 1 && `grep -c '15%' sections/projectstructre/typescript-considerations.md` >= 1 && `grep -c 'law of the instrument' sections/projectstructre/typescript-considerations.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "typescript-considerations", limit: 5 });`

## Verdict
Adopt the two-offerings distinction and make type-vs-design-usage an explicit team decision. Adapt: modern TS ergonomics narrow the gap but the DOSE question stands. Omit study-era version numbers as current evidence.
