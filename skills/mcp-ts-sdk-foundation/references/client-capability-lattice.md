<!-- capsule-v2 -->
# Client-capability requirement lattice — how does a server decide a request needs an undeclared client capability, and when does bare `elicitation: {}` count as form support?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should `-32021` MissingRequiredClientCapability be computed so nested members, implied members, and absent declarations all land correctly?

## Requirement computation
**Path/Symbol:** `packages/core-internal/src/shared/clientCapabilityRequirements.ts`: static method table (:42), `requiredClientCapabilitiesForRequest` (:48-50), `requiredClientCapabilitiesForInputRequest` (:83-108), `missingClientCapabilities` (:127-160), `isImpliedCapabilityMember` (:64-66).
**Signature:** `missingClientCapabilities(required: ClientCapabilities, declared: ClientCapabilities | undefined): ClientCapabilities | undefined`.
**Data Shape:** returns an object in `ClientCapabilities` SHAPE containing EXACTLY the missing entries — it is the `data.requiredCapabilities` payload of the `-32021` error; `undefined` = everything declared.

### Decisive source
```ts
// :64-66 the ONE implication rule
function isImpliedCapabilityMember(capability: string, member: string, declaredValue: Record<string, unknown>): boolean {
    return capability === 'elicitation' && member === 'form' && declaredValue['form'] === undefined && declaredValue['url'] === undefined;
}
```
```ts
// :87-99 input-request requirements are mode-aware
case 'elicitation/create': {
    if (entry.params?.['mode'] === 'url') return { elicitation: { url: {} } };
    return { elicitation: { form: {} } };
}
case 'sampling/createMessage': {   // tools/toolChoice present ⇒ sampling.tools
    if (params !== undefined && (params['tools'] !== undefined || params['toolChoice'] !== undefined)) return { sampling: { tools: {} } };
    return { sampling: {} }; }
```

**Flow:** top-level capability missing ⇒ whole requirement reported; present ⇒ per-MEMBER diff (`elicitation.form`, `sampling.tools`) with the bare-`{}` implication applied; declared-but-empty (`undefined` value) means NOTHING declared ⇒ every requirement missing (structural clean refusal for sessions without a per-request capability view). Three call sites share this function: HTTP-entry pre-dispatch gate, outbound MRTR input-request leg, legacy-session bridge pre-check. The static per-method table is currently EMPTY — handler-conditional needs (a specific tool wanting sampling) can't be tabled and are enforced where they arise.

**Invariant:** presence beats content for top-level keys, but the elicitation exception is deliberate 2025 back-compat: a bare `elicitation: {}` IS a form declaration (pre-mode meaning) while `elicitation:{url:{}}` opts OUT of the implication — porters who drop the exception break every 2025-era client that declared bare elicitation. Requirements are computed as data, never thrown, so callers own error shaping.

**Probe (direct tests):** `packages/core-internal/test/shared/clientCapabilityRequirements.test.ts` — describe 'missingClientCapabilities' :20, 'requiredClientCapabilitiesForInputRequest' :56, 'requiredClientCapabilitiesForRequest' :82.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "missingClientCapabilities elicitation form implied bare declaration", limit: 3 });
// → shared/clientCapabilityRequirements.missingClientCapabilities Function 127-160 rank #1
```

## Verdict
Adopt the shape-preserving diff + single implication rule; adapt your -32021 error envelope to host conventions; omit the empty static table until your protocol revision defines methods needing unconditional capabilities.
