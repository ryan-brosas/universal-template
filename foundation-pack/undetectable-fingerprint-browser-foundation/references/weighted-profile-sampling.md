<!-- capsule-v2 -->
# Weighted profile sampling — how are profiles selected to mimic real-world traffic?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** How must a profile picker choose records so synthetic fleets look like real traffic distributions?

## weight is probability mass, not decoration
**Path/Symbol:** `fingerprints/user-agents.json` field `weight` (graph Variable `fingerprints.user-agents.weight`); every record lines 2–165141.
**Signature:** `weight: number` per record; Σweight over the array ≈ 1.0.
**Data Shape:** measured distribution: Σ = 1.0000000000000058 over 10,000 records; deviceCategory mix mobile 7316 / desktop 2587 / tablet 97; individual weights ~1e-4–1e-6 scale (rare devices get tiny mass).

### Decisive source
```bash
$ jq '[.[].weight] | add' fingerprints/user-agents.json
1.0000000000000058
$ jq -r 'group_by(.deviceCategory) | map({(.[0].deviceCategory): length}) | add' fingerprints/user-agents.json
{ "desktop": 2587, "mobile": 7316, "tablet": 97 }
```

**Flow:** enumerate records → draw u ~ U(0,1) → walk cumulative weight until u < cume → that record is the session identity → repeat per fresh profile/session, not per request.
**Invariant:** selection MUST be weight-biased (cumulative or alias method). Uniform choice would inflate rare devices by orders of magnitude and produce an unnatural fleet fingerprint. Weights are calibrated externally (real-world market data), so re-normalize after any record addition/subtraction.
**Probe:** `jq '[.[].weight] | add' fingerprints/user-agents.json` → returns ~1.0 (executed pass 1; any refactor that breaks the sum-to-1 property fails this probe).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", name_pattern: "^weight$", label: "Variable", limit: 5 });
```

## Verdict
Adopt sum-to-1 weighting semantics and cumulative sampling; adapt the calibration source if you regenerate weights for your own fleet; omit uniform random selection even though it "feels" simpler. Anti-port lesson verified in-data: viewport pairs are recorded VERBATIM including 452/10000 viewport>screen rows (CrOS off-by-one, Linux VM layout viewports) — do not clamp or "fix" captured values; detectors model real browsers, warts included.
