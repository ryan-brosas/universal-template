<!-- capsule-v2 -->
# Deterministic continuation oracle — how do you prove a compacted handoff can replay real work with no model in the loop, grading filesystem state before ever running a command?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does an address-routed resume reconstruct exact task operations from persisted memory, and what ordering keeps the executable oracle honest?

## Address-routed CERT_TASK_V1 replay behind static-first fixture grading
**Path/Symbol:** `scripts/certification/context-lib.mjs`: `snapshotFiles` (:82-84), `evaluateFixtureOracle` (:86-120), `resolveInside` (:122-127), `runDeterministicHandoff` (:129-168). Direct tests: `tests/certification/context-harness.test.ts` :111-143 (executable-oracle describe; suite GREEN).
**Signature:** `runDeterministicHandoff({root, compactedContext, memory}): {taskAddress, operationCount, addressResolved}`; `evaluateFixtureOracle(root, fixture, forbiddenBefore): {passed, failures[], test:{command,args,status,stdout,stderr}}`.

### Decisive source
```ts
if (!details || details.stableAddresses?.recall !== "session-entry-id-range")
  throw new Error("Compacted context has no supported recall address");
const pointer = await memory.currentSessionPointer();
if (!pointer || typeof pointer.session !== "string" || typeof pointer.sourceHash !== "string")
  throw new Error("MemoryProvider did not issue an integrity-bound current-session pointer");
const expansion = await memory.expand({ pointer, entryIds: [taskAddress] });
const taskEntry = expansion?.expanded?.find((entry) => entry.entryId === taskAddress);
if (!taskEntry || !taskEntry.text.startsWith("CERT_TASK_V1\n"))
  throw new Error("Address did not expand to an exact CERT_TASK_V1 task");
// resolveInside(root, operation.path): throws "Task path escapes fixture" outside root
// evaluateFixtureOracle: static checks FIRST; spawnSync(…, PI_OFFLINE=1, timeout 15s)
//   runs only when failures.length === 0 — static failure leaves test.status === null
```

**Flow:** the resume side receives ONLY (1) the compacted summary/details and (2) constrained MemoryProvider pointer+expand APIs — never the session file or task operations. It demands a typed stable-address scheme, expands exactly the one task entry through an integrity-bound pointer (`session` + `sourceHash`), and only then decodes `CERT_TASK_V1\n` + JSON of typed operations (`write`, or `replace` whose `oldText` must be present). Every gap THROWS — missing address, failed expansion, wrong magic prefix, unavailable payload, escaping path — instead of inventing success. Grading is layered: expected files byte-equal, forbidden files byte-identical to their before-snapshot, unexpected files rejected against an allowlist (initial ∪ expected minus `.git/`) — and the executable Node oracle spawns at most once, only after all static checks pass.
**Invariant:** `addressResolved` is derived from whether the expansion returned the entry, never a constant; static-before-dynamic ordering means a broken artifact can't burn a 15s process run or mask file-level failures; the simulator never learns `task.operations` except through exact memory expansion, so passing proves the ADDRESS CARRIED the work across the handoff.
**Probe:** executed byte-for-byte: `grep -n "CERT_TASK_V1" scripts/certification/context-lib.mjs` → :146 (startsWith gate), :147 (throw text), :149 (slice decode); `grep -cn "Task path escapes fixture" scripts/certification/context-lib.mjs` → 1; `grep -n "PI_OFFLINE" scripts/certification/context-lib.mjs` → 109; suite GREEN (context-harness 10/10).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "runDeterministicHandoff evaluateFixtureOracle snapshotFiles resolveInside fixture oracle forbidden", limit: 6 });
```
(Rank #1–4 resolve `evaluateFixtureOracle` :86-120, `snapshotFiles` :82-84, `resolveInside` :122-127, `runDeterministicHandoff` :129-168 line-exact.)

## Verdict
Adopt static-first oracle layering (byte-equality + allowlist before any spawned check), magic-prefix envelopes decoded only AFTER integrity-bound retrieval, and throw-don't-improvise operation replay for any "did state survive the handoff?" test; adapt the address scheme, envelope tag, and operation verbs to your store; omit the MemoryProvider indirection only if your handoff already carries integrity-bound pointers — the invariant is that resume inputs are addresses plus APIs, never captured sessions.
